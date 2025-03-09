import os
import sys
import unittest
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import the module to test
from src.tools.deep_promoter_integration import DeepPromoterIntegration


class TestDeepPromoterIntegration(unittest.TestCase):
    """Test the DeepPromoterIntegration class for generating promoters and predicting expression."""
    
    def setUp(self):
        """Set up for all tests."""
        # Create a test directory in seq/ if it doesn't exist
        self.deep_promoter_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                               'ext_repos', 'Deep_promoter')
        self.seq_dir = os.path.join(self.deep_promoter_path, 'seq')
        os.makedirs(self.seq_dir, exist_ok=True)
        
        # Create a minimal sequence data file for testing
        self.sequence_data_path = os.path.join(self.seq_dir, 'sequence_data.txt')
        with open(self.sequence_data_path, 'w') as f:
            f.write('ATCGAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAG\n')
            f.write('GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC\n')
            f.write('TACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTA\n')
        
        # Create the instance - note: model_path should be set to a valid path for most tests
        # For testing, we expect this to fail if model path is not provided
        self.dpi = DeepPromoterIntegration(seq_len=50, batch_size=32)
    
    def test_initialization(self):
        """Test that the class initializes correctly."""
        self.assertEqual(self.dpi.seq_len, 50)
        self.assertEqual(self.dpi.batch_size, 32)
        self.assertFalse(self.dpi.loaded)
    
    def test_load_model_fails_without_weights(self):
        """Test that model loading fails when no valid model path is provided."""
        # Without valid model_path, this should return False
        result = self.dpi.load_model()
        self.assertFalse(result, "Model loading should fail without valid weights")
        self.assertFalse(self.dpi.loaded, "Model should not be loaded without valid weights")
    
    def test_generate_promoters_requires_model(self):
        """Test that generate_promoters requires a loaded model and fails appropriately."""
        # Without a model, this should return an empty list
        sequences = self.dpi.generate_promoters(num_sequences=2)
        self.assertEqual(sequences, [], "Should return empty list when model is not loaded")
    
    def test_predict_expression(self):
        """Test expression prediction with manually created result files."""
        # Create test sequences
        test_sequences = [
            'ATCGAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAG',
            'GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC'
        ]
        
        # Create temporary result files for testing (these would normally be created by the predictor)
        cnn_result_file = os.path.join(self.seq_dir, 'seq_exp_CNN.txt')
        with open(cnn_result_file, 'w') as f:
            f.write('seq_0\t0.75\n')
            f.write('seq_1\t0.25\n')
        
        # Call predict_expression - this will try to use the real PREDICT class
        results = self.dpi.predict_expression(test_sequences)
        
        # Cleanup
        os.remove(cnn_result_file)
        
        # Check results - this should succeed even without a loaded model
        # since we're manually creating the output files
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], 0.75)
        self.assertEqual(results[1], 0.25)
    
    def test_filter_promoters_by_expression(self):
        """Test filtering promoters by expression with manually created result files."""
        # Create test sequences
        test_sequences = [
            'ATCGAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAGTCAG',
            'GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGC'
        ]
        
        # Create temporary result files for testing
        cnn_result_file = os.path.join(self.seq_dir, 'seq_exp_CNN.txt')
        with open(cnn_result_file, 'w') as f:
            f.write('seq_0\t0.70\n')
            f.write('seq_1\t0.30\n')
            
        # Filter with min_expression = 0.5
        filtered = self.dpi.filter_promoters_by_expression(test_sequences, min_expression=0.5)
        
        # Cleanup
        os.remove(cnn_result_file)
        
        # Check results - should be testable without a loaded model since we create the output files
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0][0], test_sequences[0])
        self.assertEqual(filtered[0][1], 0.7)
    
    def test_error_handling_with_empty_input(self):
        """Test error handling with empty input."""
        # Test with empty sequences
        results = self.dpi.filter_promoters_by_expression([])
        self.assertEqual(results, [])
    
    def tearDown(self):
        """Clean up after tests."""
        # Clean up any temporary files
        if os.path.exists(self.sequence_data_path):
            os.remove(self.sequence_data_path)
        
        # Close resources
        if hasattr(self.dpi, 'session') and self.dpi.session:
            self.dpi.cleanup()


if __name__ == '__main__':
    unittest.main() 