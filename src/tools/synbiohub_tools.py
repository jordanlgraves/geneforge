from src.tools.base_tool import Tool
import dotenv
import os
dotenv.load_dotenv()
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
# ---------------------------------------------------------------------------
#  SynBioHub tools
# ---------------------------------------------------------------------------

class SynBioHubSearchTool(Tool):
    name = "synbiohub_search"
    description = (
        "Search the SynBioHub public repository (https://synbiohub.org) for SBOL objects such as parts, collections, or entire designs. "
        "This helper is read-only and returns the raw JSON/XML text emitted by the server so that downstream code—or the LLM—can parse it."
        "Example: objectType='ComponentDefinition', query='pTet', offset=0, limit=25."
    )
    parameters = {
        "type": "object",
        "properties": {
            "objectType": {"type": "string", "description": "Type of object to search for (ComponentDefinition, Collection, etc.)"},
            "sbolTag": {"type": "string", "description": "Tag in the SBOL namespace to search for (role=<http://identifiers.org/so/SO:0000316>)"},
            "collection": {"type": "string", "description": "Collection to search for (collection=<http://synbiohub.org/public/igem/igem_collection>)"},
            "dcterms": {"type": "string", "description": "Tag in the dcterms namespace to search for (title='pLac')"},
            "namespace": {"type": "string", "description": "Namespace to search for (namespace=<http://sbols.org/v2#role>)"},
            "query": {"type": "string", "description": "Search string to search for in the displayId, name, or description fields"},
            "offset": {"type": "integer", "description": "Result offset", "default": 0},
            "limit": {"type": "integer", "description": "Maximum results", "default": 20},
        },
        "required": ["objectType", "query"],
    }

    def execute(self, 
                objectType: str | None = None, 
                sbolTag: str | None = None, 
                collection: str | None = None, 
                dcterms: str | None = None, 
                namespace: str | None = None, 
                query: str | None = None, 
                offset: int | None = None, 
                limit: int | None = None):
        sbh = self.session_state.get_synbiohub_client()
        try:
            results = sbh.search(objectType, sbolTag, collection, dcterms, namespace, query, offset, limit)
            return results
        except Exception as exc:
            return {"error": str(exc)}


class SynBioHubDownloadPartTool(Tool):
    name = "synbiohub_download_part"
    description = (
        "Download a single SynBioHub object identified by its URI and return it in the requested format "
        "('sbol', 'fasta', 'gb', 'gff', 'metadata', or 'sbolnr'). The binary response is UTF-8-decoded and truncated to the first 5 kB so the assistant can preview it."
        " Example: uri='https://synbiohub.org/public/igem/BBa_R0010/1', format='gb'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "uri": {"type": "string", "description": "Full URI of the SBH object."},
            "format": {"type": "string", "enum": ["sbol", "fasta", "gb", "gff", "metadata", "sbolnr"], "default": "sbol"},
        },
        "required": ["uri"],
    }

    def execute(self, uri: str, format: str = "sbol"):
        sbh = self.session_state.get_synbiohub_client()
        try:
            content = sbh.download_part(uri, fmt=format) # returns bytes
            # Write to a file and report the path
            str_content = content.decode("utf-8", errors="ignore")
            path = self.session_state.write_file(str_content, f"synbiohub_{uri.split('/')[-1]}.{format}")
            
            return {
                "success": True,
                "format": format,
                "bytes": len(content),
                "content_base64_truncated": str_content[:50] + '...',  # truncate
                "path": str(path),
            }
        except Exception as exc:
            return {"error": str(exc)}


class SynBioHubSubmitTool(Tool):
    name = "synbiohub_submit"
    description = (
        "Upload an SBOL/GenBank/FASTA file—or a zip archive of multiple files—to SynBioHub as a new collection. "
        "Requires valid SynBioHub user credentials configured in the SessionState client. "
        "Use 'overwrite_merge' = 0 (keep), 1 (overwrite), 2 or 3 (merge) to control how existing records are handled. Returns the raw server response text."
        " Example: file_path='my_part.xml', submission_id='MyPart', version='1', name='My Test', description='Demo submission', overwrite_merge=0."
    )
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to file to upload."},
            "submission_id": {"type": "string", "description": "ID for the submission (alphanumeric & underscore)."},
            "version": {"type": "string", "description": "Version string (e.g. '1')."},
            "name": {"type": "string", "description": "Human-readable name."},
            "description": {"type": "string", "description": "Description of the submission."},
            "citations": {"type": "string", "description": "Comma-separated PubMed IDs", "default": ""},
            "overwrite_merge": {"type": "integer", "description": "0 keep, 1 overwrite, 2/3 merge", "default": 0},
        },
        "required": ["file_path", "submission_id", "version", "name", "description"],
    }

    def execute(self, file_path: str, submission_id: str, version: str, name: str, description: str, citations: str = "", overwrite_merge: int = 0):
        sbh = self.session_state.get_synbiohub_client()
        try:
            resp_text = sbh.submit(
                file_path=file_path,
                submission_id=submission_id,
                version=version,
                name=name,
                description=description,
                citations=citations,
                overwrite_merge=overwrite_merge,
            )
            return {"success": True, "response": resp_text}
        except Exception as exc:
            return {"error": str(exc)}

class SynBioHubSequenceSearchTool(Tool):
    name = "synbiohub_sequence_search"
    description = (
        "Run a sequence-similarity search against SynBioHub by supplying the full parameter string starting with 'sequence=' or 'globalsequence=' (e.g. 'globalsequence=ATGC...&similarity=0.9'). "
        "Maps directly to the '/search/' API and returns the raw tab-delimited text/JSON provided by the server. Example: search_params='globalsequence=ATGCGTACGTAGCTAG&id=0.9&maxaccepts=50'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "search_params": {"type": "string", "description": "Key/value search parameters beginning with sequence= or globalsequence= ..."},
        },
        "required": ["search_params"],
    }

    def execute(self, search_params: str):
        sbh = self.session_state.get_synbiohub_client()
        try:
            out = sbh.sequence_search(search_params)
            return {"success": True, "raw": out}
        except Exception as exc:
            return {"error": str(exc)}


class SynBioHubGetRelatedTool(Tool):
    name = "synbiohub_get_related"
    description = (
        "Retrieve objects related to a given SynBioHub URI using the '/related/<relation>/' endpoint. "
        "Supported relations: 'uses' (components referenced by the design), 'twins' (alternate versions), and 'similar' (homologous parts). "
        "Returns the raw JSON payload from the server. Example: uri='https://synbiohub.org/public/igem/BBa_R0010/1', relation='twins'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "uri": {"type": "string", "description": "Full URI of the SBH object."},
            "relation": {"type": "string", "enum": ["uses", "twins", "similar"], "description": "Type of relation to fetch."},
        },
        "required": ["uri", "relation"],
    }

    def execute(self, uri: str, relation: str):
        sbh = self.session_state.get_synbiohub_client()
        try:
            text = sbh.get_related(uri, relation)
            return {"success": True, "relation": relation, "raw": text}
        except Exception as exc:
            return {"error": str(exc)}
