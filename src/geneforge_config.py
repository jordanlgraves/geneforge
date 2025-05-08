import os
from pathlib import Path
from dotenv import load_dotenv

class Config:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Base paths
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.examples_dir = self.project_root / "examples"
        self.libs_dir = self.project_root / "libs"
        
        # Library paths
        self.library_json_path = self.libs_dir / "parsed" / "Eco1C1G1T0_parsed.json"
        
        # API Keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL")
        
        # LLM Settings
        self.default_model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        self.client_mode = os.getenv("CLIENT_MODE", "OPENAI")
    