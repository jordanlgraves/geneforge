#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the CircuitOptimizer class to verify integration with PromoterOptimizer.
"""

import os
import sys
import logging
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import json


# Import CircuitOptimizer
from src.library.circuit_optimizer import CircuitOptimizer
from src.tools.gpro_integration import PromoterOptimizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_circuit_optimizer")

class TestCircuitOptimizer(unittest.TestCase):
    """Test cases for the CircuitOptimizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test output directory
        self.test_output_dir = "outputs/test_circuit_optimizer"
        os.makedirs(self.test_output_dir, exist_ok=True)
        
        # Create a mock UCF file for testing
        self.mock_ucf_path = os.path.join(self.test_output_dir, "mock_ucf.json")
        with open(self.mock_ucf_path, "w") as f:
            json.dump([{"collection": "parts", "name": "pSrpR", "type": "promoter", "dnasequence": "TTGACGGCTAGCTCAGTCCTAGGTACAATGCTAGC"}], f)
        
        # Simple test Verilog code
        self.verilog_code = """
        module test_circuit(input aTc, input IPTG, output YFP);
            wire x;
            wire y;
            
            not(x, aTc);
            not(y, IPTG);
            
            or(YFP, x, y);
        endmodule
        """
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove mock UCF file if it exists
        if os.path.exists(self.mock_ucf_path):
            os.remove(self.mock_ucf_path)
    
    @patch('src.library.circuit_optimizer.list_promoters')
    @patch('src.library.circuit_optimizer.CelloIntegration')
    @patch('src.library.circuit_optimizer.UCFCustomizer')
    @patch('src.library.circuit_optimizer.PromoterOptimizer')
    @patch('src.library.circuit_optimizer.PromoterParameterPredictor')
    def test_optimize_promoters_integration(self, mock_parameter_predictor, mock_promoter_optimizer, mock_ucf_customizer, mock_cello, mock_list_promoters):
        """Test that optimize_promoters correctly integrates with PromoterOptimizer."""
        logger.info("Testing optimize_promoters integration with PromoterOptimizer")
        
        # Create mock promoter data
        test_promoter = {
            "name": "pSrpR",
            "type": "promoter", 
            "dnasequence": "TTGACGGCTAGCTCAGTCCTAGGTACAATGCTAGC",
        }
        
        # Mock the list_promoters function
        mock_list_promoters.return_value = [test_promoter]
        
        # Set up mock methods for PromoterOptimizer
        mock_optimizer_instance = mock_promoter_optimizer.return_value
        mock_optimizer_instance.predict_promoter_strength.return_value = 0.85
        mock_optimizer_instance.optimize_promoter.return_value = {
            'success': True,
            'optimized_sequence': 'TTGACGGCTAGCTCAGTCCTAGGTACAGTGCTAGC',
            'predicted_strength': 0.75
        }
        
        # Set up mock methods for UCF customizer
        mock_ucf_instance = mock_ucf_customizer.return_value
        mock_ucf_instance.find_gate_for_promoter.return_value = "gate1"
        mock_ucf_instance.get_gate_parameters.return_value = {"ymax": 10, "ymin": 0.1, "n": 2.5, "K": 0.5}
        
        # Set up mock methods for ParameterPredictor
        mock_predictor_instance = mock_parameter_predictor.return_value
        mock_predictor_instance.predict_parameters.return_value = {"ymax": 12, "ymin": 0.05, "n": 2.7, "K": 0.4}
        
        # Initialize the optimizer WITHOUT mocking its initialization
        optimizer = CircuitOptimizer(output_dir=self.test_output_dir)
        
        # Replace the instance properties with our mocks
        optimizer.promoter_optimizer = mock_optimizer_instance
        optimizer.ucf_customizer = mock_ucf_instance
        optimizer.parameter_predictor = mock_predictor_instance
        
        # Create test performance metrics
        current_iteration = {
            "metrics": {
                "success": True,
                "overall_score": 0.75,
                "average_on_off_ratio": 15.0,
                "average_leakage": 4.5,
                "on_off_ratios": {"YFP": 75.0},
                "leakage": {"YFP": 3.5}
            },
            "ucf_path": self.mock_ucf_path,
            "output_path": os.path.join(self.test_output_dir, "mock_output")
        }
        
        # Run the optimize_promoters method
        result = optimizer.optimize_promoters(current_iteration)
        
        # Check that the promoter optimizer was called with expected parameters
        mock_optimizer_instance.optimize_promoter.assert_called_once_with(
            test_promoter['dnasequence'], 
            target_strength=0.8,
            iterations=50
        )
        
        # Verify the UCF customizer was used to find gate parameters
        mock_ucf_instance.find_gate_for_promoter.assert_called_once()
        mock_ucf_instance.get_gate_parameters.assert_called_once()
        
        # Check parameter predictor was called
        mock_predictor_instance.predict_parameters.assert_called_once()
        
        # The result should contain information about the optimization
        self.assertIn('optimized_promoters', result)
        self.assertEqual(len(result['optimized_promoters']), 1)
        self.assertEqual(result['optimized_promoters'][0]['name'], 'pSrpR')


def run_tests():
    """Run all tests."""
    test_loader = unittest.TestLoader()
    test_suite = test_loader.loadTestsFromTestCase(TestCircuitOptimizer)
    unittest.TextTestRunner(verbosity=2).run(test_suite)

if __name__ == "__main__":
    logger.info("Starting CircuitOptimizer integration tests")
    run_tests()
    logger.info("CircuitOptimizer integration tests completed") 