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
        self.default_model = os.getenv("DEFAULT_MODEL", "gpt-4")
        self.client_mode = os.getenv("CLIENT_MODE", "OPENAI")
        
        # Integration Settings
        self.cello_jar_path = os.getenv("CELLO_JAR_PATH", "")
        self.ibiosim_path = os.getenv("IBIOSIM_PATH", "")
        
        # Validate required paths
        self._validate_paths()
    
    def _validate_paths(self):
        """Ensure required directories exist."""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.libs_dir / "parsed", exist_ok=True)
        
        if not self.library_json_path.exists():
            raise FileNotFoundError(f"Library file not found: {self.library_json_path}") 