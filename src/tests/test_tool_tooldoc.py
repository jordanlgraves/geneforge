import os
import sys
import unittest
import dotenv

dotenv.load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.session_state import SessionState
from src.tools.functions import ToolDocsQueryTool


class TestToolDocsQueryTool(unittest.TestCase):
    """Tests the behaviour of ToolDocsQueryTool.

    These tests perform live queries against the OpenAI assistants API, which
    requires a valid OPENAI_API_KEY to be set in the environment.
    """

    @classmethod
    def setUpClass(cls):
        """Initialise a single session state for all tests."""
        cls.session_state = SessionState()
        cls.tool = ToolDocsQueryTool(cls.session_state)

    def test_live_query(self):
        """Test a live query.

        This test creates a real assistant, thread and run. It may take time.
        It also assumes the doc files (e.g. docs/tools/cello-v2.pdf) are present.
        """
        out = self.tool.execute(tool_name="cello", query="What is a UCF file?")

        if "error" in out:
            print(f"Tool returned error: {out['error']}")

        self.assertTrue(
            out.get("success") is True or "error" in out,
            "Tool must return either success or an error message."
        )
        if out.get("success"):
            self.assertIn("answer", out)
            self.assertIsInstance(out["answer"], str)
            self.assertIn("citations", out)
            self.assertIsInstance(out["citations"], list)
    
    def test_cached_assistant_is_reused(self):
        """Test that a second query reuses the same assistant."""
        # First call (creates the single assistant)
        self.tool.execute(tool_name="prod", query="What is ProD?")
        self.assertTrue(hasattr(self.session_state, "tooldoc_assistant"))
        first_id = getattr(self.session_state, "tooldoc_assistant")
        self.assertIsNotNone(first_id)

        # Second call (should reuse the same assistant)
        self.tool.execute(tool_name="cello", query="What is SBOL?")
        self.assertTrue(hasattr(self.session_state, "tooldoc_assistant"))
        second_id = getattr(self.session_state, "tooldoc_assistant")
        
        self.assertEqual(first_id, second_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
