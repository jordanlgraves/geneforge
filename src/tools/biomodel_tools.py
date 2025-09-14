# src/tools/biomodels_tools.py
import requests, tempfile, re
from typing import Dict, Any
from src.session_state import SessionState
from src.tools.base_tool import Tool

API_BASE = "https://www.ebi.ac.uk/biomodels"

class DownloadBioModelSBMLTool(Tool):
    name = "download_biomodel_sbml"
    description = "Download curated SBML by BioModels model_id and attach it to session_state.sbml_file"
    parameters = {
        "type": "object",
        "properties": {"model_id": {"type": "string"}},
        "required": ["model_id"],
    }

    def __init__(self, session_state: SessionState):
        self.session_state = session_state

    @classmethod
    def get_openai_schema(cls):
        return {"name": cls.name, "description": cls.description, "parameters": cls.parameters}

    def _resolve_main_filename(self, model_id: str) -> str:
        """
        Try the JSON API first (requires Accept: application/json).
        If that fails, fall back to scraping the HTML 'Files' section for the download link.
        """
        files_url = f"{API_BASE}/model/files/{model_id}"
        # --- Attempt JSON API ---
        try:
            r = requests.get(files_url, headers={"Accept": "application/json"}, timeout=60)
            if r.status_code == 200 and r.headers.get("Content-Type","").startswith("application/json"):
                data = r.json()
                main = data.get("main") or []
                if main:
                    return main[0]["name"]  # e.g., 'BIOMD0000000012_url.xml'
        except Exception:
            pass  # fall through to HTML scrape

        # --- HTML scrape fallback ---
        # Fetch the model page and look for the first download link pattern
        page = requests.get(f"{API_BASE}/model/{model_id}", timeout=60)
        if page.status_code != 200:
            raise RuntimeError(f"files endpoint failed ({files_url}); page fetch http {page.status_code}")

        # Look for .../model/download/{ID}?filename=<name>
        m = re.search(rf"/biomodels/model/download/{re.escape(model_id)}\?filename=([^\"'<>]+\.xml)", page.text)
        if not m:
            raise RuntimeError("Could not locate SBML filename on model page.")
        return m.group(1)

    def execute(self, model_id: str) -> Dict[str, Any]:
        try:
            fname = self._resolve_main_filename(model_id)
        except Exception as e:
            return {"success": False, "error": f"list-files failed: {e}"}

        # Download the exact filename (allow redirects)
        dl = f"{API_BASE}/model/download/{model_id}"
        try:
            r = requests.get(dl, params={"filename": fname}, timeout=90, allow_redirects=True)
            if r.status_code != 200:
                return {"success": False, "error": f"download failed: http {r.status_code} ({r.text[:200]})"}
        except Exception as e:
            return {"success": False, "error": f"download exception: {e}"}

        fd = tempfile.NamedTemporaryFile(delete=False, suffix=".xml")
        fd.write(r.content); fd.close()
        self.session_state.set_sbml_file(fd.name)
        return {"success": True, "path": fd.name, "filename": fname}


if __name__ == "__main__":
    from src.session_state import SessionState
    session_state = SessionState()
    tool = DownloadBioModelSBMLTool(session_state)
    print(tool.execute("BIOMD0000000012"))