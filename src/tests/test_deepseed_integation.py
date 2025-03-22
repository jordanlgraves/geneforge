import unittest
import os
import shutil
import time
import json
from pathlib import Path

# Determine the absolute path to the project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

import dotenv
dotenv.load_dotenv()

from src.tools.deepseed_integration import DeepSeedIntegration

# Remove the skipUnless decorator to always run the tests
class TestCelloIntegration(unittest.TestCase):
    """
    Tests for the CelloIntegration class.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Configure logging to capture messages
        import logging
        cls.logger = logging.getLogger("TestDeepSeedIntegration")
        cls.logger.setLevel(logging.INFO)
        
        # Set the project root for use in tests
        cls.project_root = Path(__file__).resolve().parent.parent.parent
        
    def test_load_generator(self):
        integration = DeepSeedIntegration()
        integration._ensure_generator_loaded()
        self.assertIsNotNone(integration.generator)

    def test_load_promoter_predictor(self):
        integration = DeepSeedIntegration()
        integration._ensure_predictor_loaded()
        self.assertIsNotNone(integration.predictor)

    def test_predict_promoter_strength(self):
        integration = DeepSeedIntegration()
        integration._ensure_predictor_loaded()
        strength = integration.predict_promoter_strength('ATAGATAGGATAGGATATGGAGGCCGGCGATAGCCCCATA')
        self.assertIsNotNone(strength)
        self.assertGreater(strength, 0)
        self.assertLess(strength, 1)
            
if __name__ == "__main__":
    unittest.main()
    