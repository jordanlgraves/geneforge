import unittest
import os
import shutil
import time
import json
from pathlib import Path

import dotenv
dotenv.load_dotenv()

from src.tools.promoter_calculator_integration import PromoterCalculatorIntegration

# Remove the skipUnless decorator to always run the tests
class TestPromoterCalculatorIntegration(unittest.TestCase):
    """
    Tests for the PromoterCalculatorIntegration class.
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

    def test_predict_promoter_strength(self):
        integration = PromoterCalculatorIntegration()
        sequence = 'ATAGATAGGATAGGATATGGAGGCCGGCGATAGCCCCATA'
        sequence = 'A' * 20 + sequence + 'A' * 20
        output = integration.predict_promoter_strength(sequence)
        self.assertIsNotNone(output)
        self.logger.info(f"Output: {output}")
            
if __name__ == "__main__":
    unittest.main()
    