import traceback
from src.integrations.pro_d_integration import ProDIntegration, class_to_rpu
from src.tools.base_tool import Tool
import os
import dotenv
from typing import ClassVar, Dict, Any, Optional, List

from src.utils import extract_id_ecoli_spacer


dotenv.load_dotenv()
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"


class _ProDToolBase(Tool):
    """Mixin that provides a per-session ProDIntegration instance."""

    def _get_prod(self) -> ProDIntegration:
        if not hasattr(self.session_state, "prod_integration"):
            setattr(self.session_state, "prod_integration", ProDIntegration())
        return getattr(self.session_state, "prod_integration")



# ---------------------------------------------------------------------------
#  NEW Promoter library generation tools (split from deprecated GeneratePromoterLibraryWithProDTool)
# ---------------------------------------------------------------------------

class _ProDPromoterToolBase(_ProDToolBase):
    """Helper mix-in providing common promoter-centric utilities."""

    _dna_chars: ClassVar[set[str]] = set("UATGCRYSWKMBDHVNatgcryswkmbdhvnu")

    def _resolve_promoter_sequence(self, promoter: str, file_type: str = "ucf") -> Optional[str]:
        """Return full promoter DNA sequence from ID or sequence.

        If *promoter* already looks like DNA (≥17 bp consisting only of IUPAC
        characters) it is returned (upper-cased). Otherwise it is treated as a
        part ID and resolved via `LibraryManager` using *file_type* to select
        the JSON (ucf / input / output).
        """
        if set(promoter).issubset(self._dna_chars) and len(promoter) >= 17:
            return promoter.upper()

        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
            return None
        if file_type == "ucf":
            lib_data = cello_library.get_ucf_data()
        elif file_type == "input":
            lib_data = cello_library.get_input_sensor_data()
        else:
            lib_data = cello_library.get_output_device_data()
        import src.library.cello_utils as plc
        part = plc.get_part_by_name(lib_data, promoter)
        if not part:
            return None
        return part.get("dnasequence") or part.get("sequence")
    

    # ------------------------------------------------------------------
    #  Helper to auto-save variants into a custom UCF
    # ------------------------------------------------------------------

    def _auto_save_variants(
        self,
        parent_promoter: str | None,
        upstream: str,
        downstream: str,
        variants_dict: dict,
        save_to_library: str | None,
    ) -> dict:
        """Write the generated variants to a new custom UCF when requested.

        Currently only the *ucf* target is implemented.  Returns a dict that
        will be merged into the tool's success payload.
        """

        if not save_to_library:
            return {}

        if save_to_library != "ucf":
            return {"warning": f"Automatic save for '{save_to_library}' not yet supported."}

        if not parent_promoter:
            return {"error": "Parameter 'parent_promoter' is required when save_to_library is set."}

        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
            return {"error": "No library selected. Use select_library first."}

        # Build list of variant dicts with spacer & ymax
        variants_list = []
        for spacer_seq, props in variants_dict.items():
            variants_list.append({
                "spacer": spacer_seq,
                "ymax": props.get("ymax") or props.get("strength") or 1.0,
            })

        try:
            added_items = cello_library.add_promoter_variants(parent_promoter, variants_list)
            return {"draft_ucf_pending": True, "variants_saved": added_items}
        except Exception as exc:
            return {"error": str(exc)}

    @staticmethod
    def _split_flanks(promoter_seq: str, spacer: str) -> tuple[str, str]:
        """Return (upstream, downstream) regions flanking *spacer* inside *promoter_seq*."""
        idx = promoter_seq.find(spacer)
        if idx == -1:
            return "", ""
        return promoter_seq[:idx], promoter_seq[idx + 17:]

# ---------------------------------------------------------------------------
#  EstimatePromoterStrengthWithProD
# ---------------------------------------------------------------------------


class EstimatePromoterStrengthWithProDTool(_ProDToolBase):
    name = "estimate_promoter_strength_with_pro_d"
    description = "Return ProD class and calibrated ymax for a promoter ID or DNA sequence. If an ID is given the currently selected library is searched."
    parameters = {
        "type": "object",
        "properties": {
            "promoter_or_spacer": {"type": "string", "description": "Promoter name/id from the selected library or full DNA sequence or 17-bp spacer."},
            "file_type": {"type": "string", "enum": ["ucf", "input", "output"], "description": "Which library JSON to search when an ID is supplied", "default": "ucf"}
        },
        "required": ["promoter_or_spacer"]
    }

    def execute(self, promoter_or_spacer: str, file_type: str = "ucf") -> Dict[str, Any]:
        prod = self._get_prod()

        # Determine if string looks like DNA
        dna_chars = set("UATGCRYSWKMBDHVNatgcryswkmbdhvnu")
        is_dna = set(promoter_or_spacer).issubset(dna_chars) and len(promoter_or_spacer) >= 17

        sequence = None
        cello_library = self.session_state.cello_library

        if is_dna:
            sequence = promoter_or_spacer.upper()
        else:
            # treat as part ID
            if not cello_library.current_library_id:
                return {"error": "No library selected. Use select_library first.", "success": False}

            if file_type == "ucf":
                lib_data = cello_library.get_ucf_data()
            elif file_type == "input":
                lib_data = cello_library.get_input_sensor_data()
            else:
                lib_data = cello_library.get_output_device_data()

            import src.library.cello_utils as plc
            part = plc.get_part_by_name(lib_data, promoter_or_spacer)
            if not part:
                return {"error": f"Promoter ID '{promoter_or_spacer}' not found in {file_type} file."}
            sequence = part.get("dnasequence") or part.get("sequence")
            if not sequence:
                return {"error": f"Promoter part '{promoter_or_spacer}' lacks dna sequence field."}

        # Evaluate via ProD
        result = prod.evaluate_spacers([sequence])
        if not result:
            return {"error": "ProD evaluation returned no result.", "success": False}

        if 'error' in result:
            return result
        
        cls_val = int(result[sequence])
        ymax = result.get(sequence + "_ymax", class_to_rpu(cls_val))
        spacer = extract_id_ecoli_spacer(sequence)
        
        return {
            "sequence": sequence,
            "spacer": spacer,
            "class": cls_val,
            "ymax": ymax,
            "success": True
        }

class GetSpacerFromPromoterTool(_ProDPromoterToolBase):
    name = "get_spacer_from_promoter"
    description = "Extract the 17-bp spacer from a full promoter sequence or part id/name from the selected library."
    parameters = {
        "type": "object",
        "properties": {"promoter": {"type": "string", "description": "Full promoter sequence or part id/name from the selected library."},
                       "file_type": {"type": "string", "enum": ["ucf", "input", "output"], "default": "ucf"}},
        "required": ["promoter"]
    }
    
    def execute(self, promoter: str, file_type: str = "ucf") -> Dict[str, Any]:
        prod = self._get_prod()

        # if promoter is a part id/name, resolve the sequence
        sequence = self._resolve_promoter_sequence(promoter, file_type)
        if not sequence:
            return {"error": f"Error in promoter id/name or sequence: '{promoter}'."}
        
        spacer = prod.extract_spacer(sequence)
        if spacer:
            return {"spacer": spacer, "success": True}

        else:
            return {"error": "Could not extract spacer from the provided promoter sequence."}



class GeneratePromoterLibraryFromSpacerTool(_ProDPromoterToolBase):
    name = "generate_library_from_spacer"
    description = (
        "Use ProD to generate promoter spacer variants from a **17-nt degenerate spacer blueprint**. "
        "The `blueprint` string *must be exactly 17 nucleotides long* **and must contain at least one degenerate IUPAC code** (e.g. N, R, Y, S, K, M, W, B, D, H or V); supplying a fully specified 17-mer will raise an error. "
        "If `parent_promoter` is supplied, the tool stitches every newly generated spacer between the upstream and downstream flanks of that promoter and returns complete promoter sequences together with calibrated `ymax` values."
    )
    parameters = {
        "type": "object",
        "properties": {
            "blueprint": {"type": "string", "description": "Degenerate 17-bp spacer (must contain ≥1 IUPAC ambiguity code)."},
            "desired_strengths": {"type": "array", "items": {"type": "integer"}, "description": "Strength classes ranging from 0 to 10."},
            "sequences_per_class": {"type": "integer", "default": 5},
            "parent_promoter": {"type": "string", "description": "Optional promoter ID or sequence providing flanks."},
            "file_type": {"type": "string", "enum": ["ucf", "input", "output"], "default": "ucf"},
            "save_to_library": {"type": "string", "enum": ["ucf", "input", "output"], "description": "Automatically write the generated variants to the selected library (valid only for 'ucf' file type for now)."}
        },
        "required": ["blueprint"],
    }

    def execute(
        self,
        blueprint: str,
        desired_strengths: List[int] | None = None,
        sequences_per_class: int = 5,
        parent_promoter: str | None = None,
        file_type: str = "ucf",
        save_to_library: str | None = None,
    ) -> Dict[str, Any]:
        prod = self._get_prod()
        if len(blueprint) != 17:
            return {"error": f"Blueprint must be exactly 17 bp. Provided blueprint {blueprint} is length {len(blueprint)}."}

        upstream = downstream = None
        if parent_promoter:
            parent_seq = self._resolve_promoter_sequence(parent_promoter, file_type)
            if not parent_seq:
                return {"error": f"Could not resolve parent promoter '{parent_promoter}'."}
            from src.utils import extract_id_ecoli_spacer
            spacer_parent = extract_id_ecoli_spacer(parent_seq)
            if spacer_parent and spacer_parent in parent_seq:
                upstream, downstream = self._split_flanks(parent_seq, spacer_parent)

        try:
            variants_dict = prod.generate_library(
                blueprint,
                desired_strengths=desired_strengths,
                library_size=sequences_per_class,
            )
        except IndexError as exc:
            # ------------------------------------------------------------------
            #  Guidance for LLM agents (and human users) on how to resolve the
            #  typical IndexError raised inside ProD when the sampled variant
            #  pool is missing one or more requested strength classes.
            #
            #  We surface a **single, explanatory** error string so that agent
            #  frameworks that rely on a unified {"error": str} contract can
            #  present the hint verbatim to the end-user.
            # ------------------------------------------------------------------
            return {
                "error": (
                    "ProD could not generate a complete spacer library: the 100 k-variant "
                    "sample evaluated did not contain at least one spacer for every "
                    "requested promoter strength class.\n\n"
                    "How to fix: \n"
                    "  • Reduce `sequences_per_class` (e.g. from 5 to 3).\n"
                    "  • Restrict `desired_strengths` to a subset (e.g. [2,3,4] instead of 0-10).\n"
                    "  • Make the blueprint more degenerate (add N/R/Y/S/K/M/W/B/D/H/V codes) so "
                    "    that more unique spacers are possible.\n"
                    "  • Re-run the tool: each invocation samples a different 100 k subset and may "
                    "    succeed by chance if the search space is large enough.\n\n"
                    "Background: The ProD algorithm samples up to 1e5 random spacers from the "
                    "blueprint. If none fall into a required class, the downstream consensus "
                    "builder receives an empty set and triggers an IndexError."
                )
            }
        except Exception as exc:
            return {"error": f"Error generating promoter library: {exc}"}

        if upstream is not None and downstream is not None:
            for spacer_seq, props in variants_dict.items():
                props["promoter_sequence"] = f"{upstream.upper()}{spacer_seq}{downstream.upper()}"

        return {
            "blueprint": blueprint,
            "variants": [{"spacer": s, **p} for s, p in variants_dict.items()],
            **(self._auto_save_variants(parent_promoter, upstream, downstream, variants_dict, save_to_library) if save_to_library else {}),
            "success": True,
        }



class GeneratePromoterLibraryFromPromoterTool(_ProDPromoterToolBase):
    name = "generate_library_from_promoter"
    description = (
        "Use ProD to create spacer variants by mutating an existing promoter. "
        "`mutable_positions` must be a dictionary whose *keys are spacer indices 0–16* (0 is the first base) and whose *values are IUPAC ambiguity codes* such as N, R, Y, S, K, M, W, B, D, H or V. "
        "If `promoter` is supplied as a part name/id from the selected library, `mutable_positions` is *required* so that at least one degenerate base is introduced; without it the blueprint would be non-degenerate and ProD will abort. "
        "If `promoter` is supplied as a full DNA sequence and its spacer already contains ≥ 1 ambiguity code, `mutable_positions` may be omitted. "
        "The tool returns a list of variants with their spacer sequence, predicted class/strength, calibrated `ymax`, and full promoter sequence (flanks from the parent promoter)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "promoter": {"type": "string", "description": "Promoter ID/name from the selected library or a full promoter sequence."},
            "mutable_positions": {"type": "object", "description": "Dict spacer_index to IUPAC ambiguity code (0-16)."},
            "desired_strengths": {"type": "array", "items": {"type": "integer"}, "description": "Strength classes (0-10)."},
            "sequences_per_class": {"type": "integer", "default": 5},
            "file_type": {"type": "string", "enum": ["ucf", "input", "output"], "default": "ucf"},
            "save_to_library": {"type": "string", "enum": ["ucf", "input", "output"], "description": "Automatically write the generated variants to a custom library file (valid only for 'ucf' for now)."},
        },
        "required": ["promoter"],
    }

    def execute(
        self,
        promoter: str,
        mutable_positions: Dict[str, str] | None = None,
        desired_strengths: List[int] | None = None,
        sequences_per_class: int = 5,
        file_type: str = "ucf",
        save_to_library: str | None = None,
    ) -> Dict[str, Any]:
        from src.utils import extract_id_ecoli_spacer
        prod = self._get_prod()

        parent_seq = self._resolve_promoter_sequence(promoter, file_type)
        if not parent_seq:
            return {"error": f"Could not resolve promoter '{promoter}' as a DNA sequence or a name/id."}

        spacer_parent = extract_id_ecoli_spacer(parent_seq)
        if not spacer_parent:
            return {"error": f"Failed to extract 17-bp spacer from promoter sequence: {parent_seq}."}

        spacer_chars = list(spacer_parent.upper())

        # If mutable_positions is provided, mutate the spacer
        if mutable_positions:       
            for pos_str, iupac in mutable_positions.items():
                try:
                    idx = int(pos_str)
                except ValueError:
                    return {"error": f"Index '{pos_str}' is not an integer."}
                if idx < 0 or idx > 16:
                    return {"error": "Mutable indices must be between 0 and 16."}
                spacer_chars[idx] = iupac.upper()
        else:
            # If mutable_positions is not provided, check that the spacer contains at least one IUPAC ambiguity code
            if not any(c in "N" for c in spacer_chars):
                return {"error": """The algorithm requires that the spacer sequence contain at least one IUPAC ambiguity code in order to """ +
                        """determine the blueprint sequence. Please provide `mutable_positions` to mutate the spacer or provide `promoter` """ +
                        """as  DNA sequence containing at least one IUPAC ambiguity code within a spacer region."""}

        blueprint = "".join(spacer_chars)

        try:
            variants_dict = prod.generate_library(
                blueprint,
                desired_strengths=desired_strengths,
                library_size=sequences_per_class,
            )
            if "error" in variants_dict:
                return {"error": variants_dict["error"]}

        except Exception as exc:
            return {"error": f"Error generating promoter library: {exc}"}

        upstream, downstream = self._split_flanks(parent_seq, spacer_parent)
        for spacer_seq, props in variants_dict.items():
            props["promoter_sequence"] = f"{upstream.upper()}{spacer_seq}{downstream.upper()}"

        return {
            "blueprint": blueprint,
            "parent_promoter": promoter,
            "variants": [{"spacer": s, **p} for s, p in variants_dict.items()],
            **(self._auto_save_variants(promoter, upstream, downstream, variants_dict, save_to_library) if save_to_library else {}),
            "success": True,
        }

# ---------------------------------------------------------------------------
#  PatchUcfWithPromotersTool – wraps LibraryManager.create_custom_ucf
# ---------------------------------------------------------------------------

class PatchUcfWithPromotersTool(Tool):
    name = "patch_ucf_with_promoters"
    description = (
        "Duplicate or replace a promoter part in the current library UCF with supplied spacer variants (each spacer must be 17 nt) and their calibrated `ymax` values. "
        "Returns the file path of the newly written custom UCF."
    )
    parameters = {
        "type": "object",
        "properties": {
            "parent_promoter_id": {"type": "string", "description": "ID of the promoter part to duplicate / replace."},
            "variants": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "spacer": {"type": "string"},
                        "ymax": {"type": "number"}
                    },
                    "required": ["spacer", "ymax"]
                },
                "description": "List of new spacer variants with calibrated ymax values."
            },
            "replace_parent": {"type": "boolean", "default": False, "description": "If true, parent promoter is replaced; otherwise duplicated with _varN suffix."}
        },
        "required": ["parent_promoter_id", "variants"]
    }

    def execute(self, parent_promoter_id: str, variants: List[Dict[str, Any]], replace_parent: bool = False):
        import copy
        from src.utils import extract_id_ecoli_spacer
        import src.library.cello_utils as plc

        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
            return {"error": "No library selected. Use select_library first."}

        base_ucf = cello_library.get_ucf_data()
        if not base_ucf:
            return {"error": "Failed to retrieve current UCF data."}
        
        parent_part = plc.get_part_by_name(base_ucf, parent_promoter_id)
        if not parent_part:
            return {"error": f"Parent promoter {parent_promoter_id} not found in UCF."}

        parent_seq = parent_part.get("dnasequence") or parent_part.get("sequence")
        spacer_parent = extract_id_ecoli_spacer(parent_seq)
        if not spacer_parent:
            return {"error": "Could not extract spacer from parent promoter sequence."}

        idx = parent_seq.find(spacer_parent)
        upstream = parent_seq[:idx]
        downstream = parent_seq[idx+17:]

        modified_parts = {}

        for i, var in enumerate(variants):
            spacer = var.get("spacer")
            ymax = var.get("ymax")
            if not spacer or len(spacer) != 17:
                continue
            new_seq = f'{upstream.upper()}{spacer}{downstream.upper()}'
            new_part = copy.deepcopy(parent_part)
            new_id = parent_promoter_id if (replace_parent and i == 0) else f"{parent_promoter_id}_var{i+1}"
            new_part["name"] = new_id
            if "dnasequence" in new_part:
                new_part["dnasequence"] = new_seq
            else:
                new_part["sequence"] = new_seq

            # Update ymax parameter
            updated = False
            for p in new_part.get("parameters", []):
                if p.get("parameter", "").lower() in ("ymax", "y_max"):
                    p["value"] = ymax
                    updated = True
                    break
            if not updated:
                new_part.setdefault("parameters", []).append({
                    "parameter": "ymax",
                    "value": ymax
                })
            modified_parts[new_id] = new_part

        # Call LibraryManager to write custom UCF
        try:
            cello_library.create_custom_ucf(
                selected_gates=None,
                selected_parts=list(modified_parts.keys()),
                modified_parts=list(modified_parts.values()),
                ucf_name=f"custom_{cello_library.current_library_id}_{parent_promoter_id}_variants.UCF.json",
                output_dir=self.session_state.output_directory
            )
            return {"success": True, "n_variants": len(modified_parts)}
        except Exception as e:
            if DEBUG_MODE:
                traceback.print_exc()
                raise e
            else:
                return {"error": f"Failed to patch UCF: {e}"}



class AddPromoterVariantTool(Tool):
    name = "add_promoter_variant"
    description = (
        "Create a new promoter variant by copying an existing promoter (and all dependent structures/gates/models) and replacing its 17-bp spacer with a new 17-bp spacer sequence. "
        "`ymax` (calibrated RPU) is mandatory so that associated models remain consistent. `new_promoter_id` must be alphanumeric only, no spaces or special characters."
    )
    parameters = {
        "type": "object",
        "properties": {
            "parent_promoter_id": {"type": "string", "description": "ID of the reference promoter part from the selected library."},
            "spacer_sequence": {"type": "string", "description": "17-bp spacer sequence to use in replacement of the 17-bp spacer sequence of the parent promoter"},
            "ymax": {"type": "number", "description": "Calibrated RPU (ymax) for the new promoter. Can be found in the output from the ProD tool."},
            "new_promoter_id": {"type": "string", "description": "Optional name for the new promoter. Alphanumeric characters only, no spaces or special characters."},
        },
        "required": ["parent_promoter_id", "spacer_sequence", "ymax"],
    }

    def execute(
        self,
        parent_promoter_id: str,
        spacer_sequence: str,
        ymax: float,
        new_promoter_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        import copy
        from src.utils import extract_id_ecoli_spacer
        import src.library.cello_utils as plc
        

        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
            return {"error": "No library selected. Use select_library first."}

        ucf_data = cello_library.get_ucf_data()
        if not ucf_data:
            return {"error": "Could not load UCF data."}

        parent_part = plc.get_part_by_name(ucf_data, parent_promoter_id)
        if not parent_part:
            return {"error": f"Parent promoter {parent_promoter_id} not found."}

        parent_seq = parent_part.get("dnasequence") or parent_part.get("sequence")
        spacer_parent = extract_id_ecoli_spacer(parent_seq)
        if not spacer_parent:
            return {"error": "Unable to extract spacer from parent promoter."}
        if len(spacer_sequence) != 17:
            return {"error": "Provided spacer must be 17 bp."}

        # Build new promoter sequence
        idx = parent_seq.find(spacer_parent)
        new_sequence = f"{parent_seq[:idx].upper()}{spacer_sequence.upper()}{parent_seq[idx+17:].upper()}"

        # Determine new promoter id
        if not new_promoter_id:
            base = parent_promoter_id.rstrip("\n")
            new_promoter_id = f"{base}var1"
            i = 1
            while plc.get_part_by_name(ucf_data, new_promoter_id):
                i += 1
                new_promoter_id = f"{base}var{i}"
        else: # Check that new_promoter_id is alphanumeric only
            if not new_promoter_id.isalnum():
                return {"error": "new_promoter_id must be alphanumeric only."}
        
        # Duplicate dependencies
        new_items, gate_map = plc.duplicate_promoter_dependencies(
            ucf_data, parent_promoter_id, new_promoter_id, new_sequence, ymax
        )

        # Update ymax inside associated models
        for item in new_items:
            if item.get("collection") == "models":
                # update / insert parameter
                updated = False
                for p in item.get("parameters", []):
                    if p.get("name").lower() in ("ymax", "y_max"):
                        p["value"] = ymax
                        updated = True
                        break
                if not updated:
                    item.setdefault("parameters", []).append({"name": "ymax", "value": ymax})

        # Assemble new custom UCF
        try:
            path = cello_library.create_custom_ucf(
                selected_gates=None,
                selected_parts=None,
                modified_parts=None,
                new_parts=new_items,
                ucf_name=f"custom_{cello_library.current_library_id}_{new_promoter_id}.UCF.json",
                output_dir=self.session_state.output_directory
            )
            cello_library.load_custom_ucf(path)
            self.session_state.custom_ucf_path = path
            return {
                "success": True,
                # "custom_ucf_path": path,
                "new_promoter_id": new_promoter_id,
                "added_items": new_items,
            }
        except Exception as exc:
            if DEBUG_MODE:
                traceback.print_exc()
                raise e
            return {"error": str(exc)}


class RemovePromoterTool(Tool):
    name = "remove_promoter"
    description = "Remove a promoter part and all dependent structures, gates and models from the current UCF and write a custom UCF file."
    parameters = {
        "type": "object",
        "properties": {
            "promoter_id": {"type": "string", "description": "ID of the promoter to remove."},
        },
        "required": ["promoter_id"],
    }

    def execute(self, promoter_id: str) -> Dict[str, Any]:
        import src.library.cello_utils as plc
        import json
        import os
        cello_library = self.session_state.cello_library
        if not cello_library.current_library_id:
            return {"error": "No library selected. Use select_library first."}

        ucf = cello_library.get_ucf_data()
        if not ucf:
            return {"error": "Could not load UCF data."}

        if not plc.get_part_by_name(ucf, promoter_id):
            return {"error": f"Promoter {promoter_id} not found."}

        # Use the correct utility function to remove the part and its dependencies
        new_ucf_data, summary = plc.remove_part_and_dependencies(ucf, promoter_id)

        # Write the new custom UCF to a file
        try:
            output_dir = "outputs/custom_ucf"
            os.makedirs(output_dir, exist_ok=True)
            ucf_name = f"custom_{cello_library.current_library_id}_without_{promoter_id}.UCF.json"
            path = os.path.join(output_dir, ucf_name)

            with open(path, "w") as f:
                json.dump(new_ucf_data, f, indent=2)

            # Update the library manager's state
            cello_library.load_custom_ucf(path)
            self.session_state.custom_ucf_path = path

            return {
                "success": True,
                # "custom_ucf_path": path,
                "removed_items_summary": summary,
            }
        except Exception as exc:
            if DEBUG_MODE:
                traceback.print_exc()
                raise exc
            return {"error": str(exc)}

if __name__ == "__main__":
    
    prod = ProDIntegration()
    result = prod.evaluate_spacers(["UGACGTACGGTGGAATCTGATTCGTTACCAATTGACATGATACGAAACGTACCGTATCGTTAAGGT"])
    print(result)