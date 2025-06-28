import os
import mimetypes
import requests

# ---------------------------------------------------------------------------
#  Optional import for SBOL-3 → SBOL-2 down-conversion.  We keep it lazy so
#  that users who only work with SBOL-2 do not need the extra dependency at
#  runtime.
# ---------------------------------------------------------------------------
try:
    from sbol_utilities import conversion as _sbol_conversion  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – optional runtime dependency
    _sbol_conversion = None  # Will trigger a helpful error message if needed

class SBOL2SBMLConverter:
    def __init__(self, base_api_url: str):
        self.base_api_url = base_api_url

    def convert_sbol_to_sbml(self, sbol_file_path: str, output_file_name: str) -> str:
        if not output_file_name.endswith(".zip"):
            raise ValueError("Output file name must end with .zip")

        # ------------------------------------------------------------------
        # 0) Sanity-check & auto-convert SBOL-3 to SBOL-2 if required
        # ------------------------------------------------------------------
        if not os.path.isfile(sbol_file_path):
            raise FileNotFoundError(f"SBOL file not found: {sbol_file_path}")

        # Peek at the XML/RDF prolog to detect SBOL namespace version
        with open(sbol_file_path, "r", encoding="utf-8", errors="ignore") as _fh:
            header_chunk = _fh.read(2048)

        is_sbol3 = "http://sbols.org/v3#" in header_chunk

        if is_sbol3:
            # Convert once and cache next to the original file
            prepared_path = (
                os.path.splitext(sbol_file_path)[0] + "_prepared_sbol2.xml"
            )

            # Only regenerate if the prepared file is missing or older
            if (not os.path.exists(prepared_path) or
                os.path.getmtime(prepared_path) < os.path.getmtime(sbol_file_path)):
                if _sbol_conversion is None:
                    raise RuntimeError(
                        "SBOL-3 file detected but `sbol_utilities` is not installed. "
                        "Install it or provide SBOL-2 input."
                    )
                self.prepare_sbol3_for_sbml(sbol_file_path, prepared_path)

            # Use the SBOL-2 path henceforth
            sbol_file_path = prepared_path

        mime_type, _ = mimetypes.guess_type(sbol_file_path)
        mime_type =  "application/xml"        
        files = { "sbol": (os.path.basename(sbol_file_path), open(sbol_file_path, "rb"), mime_type)}
        data = {
            "topModelId": "topModel", # Optional – change if you'd like a custom name for the top model file
            # Enable Cello-specific structural conversion logic on the server
            "cello": "true",
        }
        try:
            response = requests.post(f"{self.base_api_url}/sync/convert", files=files, data=data) #, timeout=60)
        except requests.exceptions.RequestException as exc:
            raise SystemExit(f"Request failed: {exc}") from exc
        finally:
            files["sbol"][1].close()

        if response.status_code == 200:
            content = response.content
            # output_file_name will be a zip file
            with open(output_file_name, "wb") as f:
                f.write(content)
            print(f"✅ Conversion succeeded. Output written to {output_file_name}")
            return output_file_name
        else:
            print(
                f"❌ Conversion failed with status {response.status_code}\n"
                f"Response body:\n{response.text}"
            )
            return None

    # ------------------------------------------------------------------
    #  Convenience helper – public because tests rely on it
    # ------------------------------------------------------------------
    @staticmethod
    def prepare_sbol3_for_sbml(input_path: str, output_path: str) -> str:
        """Convert an SBOL-3 document to SBOL-2 and write it to *output_path*.

        The implementation relies on the *sbol_utilities* package, which
        provides a high-fidelity graph translation.  The output is written in
        RDF/XML format so that downstream SBOL-2 → SBML converters (e.g.
        iBioSim) can process it unchanged.
        """

        if _sbol_conversion is None:
            raise RuntimeError(
                "sbol_utilities is required for SBOL-3→SBOL-2 conversion but is "
                "not installed.  Install with `pip install sbol_utilities`."
            )

        import sbol3
        import sbol2
        from sbol2 import SBOL_ACCESS_PUBLIC, SBOL_DIRECTION_NONE  # type: ignore
        from rdflib import URIRef

        # ------------------------------------------------------------------
        # Cello writes RDF/XML even if the filename ends with `.nt`, so we
        # force `file_format='xml'`.
        # ------------------------------------------------------------------

        doc3 = sbol3.Document()
        doc3.read(input_path, file_format="xml")

        # ------------------------------------------------------------------
        # Convert SBOL-3 → SBOL-2 using sbol_utilities, *then* ensure at least
        # one ModuleDefinition exists because iBioSim requires it.
        # ------------------------------------------------------------------
        doc2: sbol2.Document = _sbol_conversion.convert3to2(doc3)  # type: ignore

        # ------------------------------------------------------------------
        # The sbol_utilities back-port may leave role URIs as text literals
        # (e.g., "sbol3.SO_PROMOTER"). We map these to valid Sequence Ontology
        # URIs, otherwise the Java converter cannot identify component types.
        # ------------------------------------------------------------------
        SO_BASE = "http://identifiers.org/so/"
        SO_ROLE_MAP = {
            "sbol3.SO_PROMOTER":  SO_BASE + "SO:0000167",
            "sbol3.SO_CDS":       SO_BASE + "SO:0000316",
            "sbol3.SO_RBS":       SO_BASE + "SO:0000139",
            "sbol3.SO_TERMINATOR":SO_BASE + "SO:0000141",
        }

        for cd in list(doc2.componentDefinitions):
            updated_roles = []
            for role in cd.roles:
                role_str = str(role)
                # The role might be a full URI or a file-based one from bad parsing
                if role_str.startswith("http"):
                    updated_roles.append(role)
                else:
                    for key, mapped_uri in SO_ROLE_MAP.items():
                        if key in role_str:
                            updated_roles.append(URIRef(mapped_uri))
                            break
            cd.roles = updated_roles

        if len(doc2.moduleDefinitions) == 0:
            module_def = sbol2.ModuleDefinition("topModule", "1")
            doc2.add(module_def)

            for cd in doc2.componentDefinitions:
                # FunctionalComponent signature: uri/displayId, definition, access, direction
                # We keep the displayId identical to the ComponentDefinition for
                # traceability. The library will expand it into the current
                # default namespace and append a version number automatically.
                functional_component = sbol2.FunctionalComponent(
                    cd.displayId,
                    "",  # leave blank initially; set below for clarity
                    SBOL_ACCESS_PUBLIC,
                    SBOL_DIRECTION_NONE,
                )
                # Explicitly wire the definition URI. Some pySBOL2 versions do
                # not persist the constructor argument in RDF unless set later.
                functional_component.definition = cd.identity
                module_def.functionalComponents.add(functional_component)

            # A Model element is optional for iBioSim; omit for simplicity.

        # Ensure target directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        doc2.write(output_path)
        return output_path

if __name__ == "__main__":
    import libsbml
    # REFERENCE_SBOL_FILE = 'outputs/cello_run/not_gate_design/output/main.v/main.v_ucf._pySBOL3.nt'
    REFERENCE_SBOL_FILE = 'notebooks/sbol_to_sbml/GeneticToggleSwitch/GeneticToggleSwitch.rdf'
    assert (os.path.isfile(REFERENCE_SBOL_FILE))
    url = "http://localhost:4000"
    SBOL2SBMLConverter(url).convert_sbol_to_sbml(REFERENCE_SBOL_FILE, 
                                              "outputs/convert_test/GeneticToggleSwitch.zip")
    
