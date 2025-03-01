import os
import sys
import unittest
import logging
from pathlib import Path

from src.tools.cello_integration import CelloIntegration

class TestCircuitMetricsExtraction(unittest.TestCase):
    """Tests for extracting and evaluating circuit performance metrics from Cello output"""

    def setUp(self):
        """Set up the test environment"""
        self.logger = logging.getLogger("TestMetrics")
        self.logger.setLevel(logging.INFO)
        self.cello = CelloIntegration()
        
        # Path to the test output directory
        self.test_output_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "outputs", "cello_test_outputs", "test_NOT_gate.v"
        )
        
        # Verify the test output directory exists
        if not os.path.exists(self.test_output_path):
            self.logger.error(f"Test output path does not exist: {self.test_output_path}")
            self.skipTest("Test output directory not found")

    def test_circuit_score_extraction(self):
        """Test extraction of circuit score from circuit_score.csv"""
        metrics = self.cello.evaluate_circuit_performance(self.test_output_path)
        
        # Debugging: Print metrics
        print("\nMetrics dictionary:", metrics)
        
        # Verify the function executed successfully
        self.assertTrue(metrics['success'], f"Metrics extraction failed: {metrics.get('error')}")
        
        # Verify circuit score was extracted
        self.assertIsNotNone(metrics['overall_score'], "Circuit score should not be None")
        self.assertGreater(metrics['overall_score'], 0, "Circuit score should be greater than 0")
        
        # Log the extracted score for manual verification
        self.logger.info(f"Extracted circuit score: {metrics['overall_score']}")

    def test_activity_table_extraction(self):
        """Test extraction of input/output states and ON/OFF ratios from activity_table.csv"""
        metrics = self.cello.evaluate_circuit_performance(self.test_output_path)
        
        # Verify the function executed successfully
        self.assertTrue(metrics['success'], f"Metrics extraction failed: {metrics.get('error')}")
        
        # Verify input/output states were extracted
        self.assertIsInstance(metrics['input_output_states'], list, "Input/output states should be a list")
        self.assertGreater(len(metrics['input_output_states']), 0, "Should have at least one input/output state")
        
        # Verify ON/OFF ratios were calculated
        self.assertIsInstance(metrics['on_off_ratios'], dict, "ON/OFF ratios should be a dictionary")
        self.assertGreater(len(metrics['on_off_ratios']), 0, "Should have at least one ON/OFF ratio")
        
        # Verify leakage values were calculated
        self.assertIsInstance(metrics['leakage'], dict, "Leakage should be a dictionary")
        self.assertGreater(len(metrics['leakage']), 0, "Should have at least one leakage value")
        
        # Log the extracted metrics for manual verification
        for output, ratio in metrics['on_off_ratios'].items():
            self.logger.info(f"ON/OFF ratio for {output}: {ratio}")
            self.logger.info(f"Leakage for {output}: {metrics['leakage'].get(output, 'N/A')}%")

    def test_derived_metrics(self):
        """Test calculation of derived metrics from basic metrics"""
        metrics = self.cello.evaluate_circuit_performance(self.test_output_path)
        
        # Verify the function executed successfully
        self.assertTrue(metrics['success'], f"Metrics extraction failed: {metrics.get('error')}")
        
        # Verify dynamic range was calculated
        self.assertIsInstance(metrics['dynamic_range'], dict, "Dynamic range should be a dictionary")
        self.assertGreater(len(metrics['dynamic_range']), 0, "Should have at least one dynamic range value")
        
        # Verify average metrics were calculated
        self.assertIsNotNone(metrics['average_on_off_ratio'], "Average ON/OFF ratio should not be None")
        self.assertIsNotNone(metrics['average_leakage'], "Average leakage should not be None")
        
        # Verify performance standards were evaluated
        self.assertIsInstance(metrics['meets_performance_standards'], dict, 
                             "Performance standards evaluation should be a dictionary")
        
        # Log the derived metrics for manual verification
        self.logger.info(f"Average ON/OFF ratio: {metrics['average_on_off_ratio']}")
        self.logger.info(f"Average leakage: {metrics['average_leakage']}%")
        
        for output, standards in metrics['meets_performance_standards'].items():
            self.logger.info(f"Performance standards for {output}:")
            self.logger.info(f"  - Meets ON/OFF ratio standard: {standards['on_off_ratio']}")
            self.logger.info(f"  - Meets leakage standard: {standards['leakage']}")

    def test_full_metrics_report(self):
        """Test the full metrics report and verify data structure"""
        metrics = self.cello.evaluate_circuit_performance(self.test_output_path)
        
        # Expected keys in the metrics dictionary
        expected_keys = [
            'overall_score', 
            'input_output_states', 
            'on_off_ratios', 
            'leakage', 
            'dynamic_range', 
            'part_usage',
            'average_on_off_ratio',
            'average_leakage',
            'meets_performance_standards',
            'success',
        ]
        
        # Verify all expected keys are present
        for key in expected_keys:
            self.assertIn(key, metrics, f"Metrics should contain '{key}'")
        
        # Print the full metrics report for manual verification
        self.logger.info("Full metrics report:")
        for key, value in metrics.items():
            if isinstance(value, dict) and len(value) > 3:
                self.logger.info(f"{key}: {type(value)} with {len(value)} items")
            else:
                self.logger.info(f"{key}: {value}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the tests
    unittest.main() 