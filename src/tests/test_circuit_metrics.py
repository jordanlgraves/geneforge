import os
import shutil
import sys
import unittest
import logging
from pathlib import Path

from src.tools.cello_integration import CelloIntegration

class TestCircuitMetricsExtraction(unittest.TestCase):
    """Tests for extracting and evaluating circuit performance metrics from Cello output"""

    @classmethod
    def setUpClass(cls):
        """Set up the test environment"""
        cls.logger = logging.getLogger("TestMetrics")
        cls.logger.setLevel(logging.INFO)
        cls.cello = CelloIntegration()

        cls.test_verilog_code = """module Main(in1, out1);
  output out1;
  input in1;  
  
  assign g1 = ~in1;
  
  assign out1 = g1;
  
  endmodule"""

        cls.run_name = "unittest_NOT_gate_circuit_metrics"
        cls.test_run_directory = os.path.join(
            "outputs", "cello_run", cls.run_name
        )
        cls.test_output_path = os.path.join(
            cls.test_run_directory, 'output', 'main.v'
        )

        # run cello to generate the test output unless it already exists
        if not os.path.exists(cls.test_output_path):
            # get first library starting with 'Eco'
            libs = cls.cello.get_available_libraries()
            default_lib = next((lib for lib in libs if lib.startswith('Eco')), None)
            cls.cello.select_library(default_lib)
            results = cls.cello.run_cello(run_name=cls.run_name, verilog_code=cls.test_verilog_code)
            print(results)
        
    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_run_directory):
            shutil.rmtree(cls.test_run_directory)

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