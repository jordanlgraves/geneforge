import os
import sys
import numpy as np
import tensorflow as tf
from typing import List, Dict, Tuple, Optional, Union
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add Deep_promoter to path if not already added
deep_promoter_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ext_repos', 'Deep_promoter')
if deep_promoter_path not in sys.path:
    sys.path.append(deep_promoter_path)

# Import Deep_promoter modules
try:
    import language_helpers
    from predictor import PREDICT
except ImportError as e:
    logger.error(f"Error importing Deep_promoter modules: {e}")
    logger.error("Make sure all dependencies are installed and the path is correct")


class DeepPromoterIntegration:
    """
    Integration class for Deep_promoter functionality.
    Provides methods to generate new promoter sequences and predict their expression levels.
    Uses the original Deep_promoter code directly.
    """
    
    def __init__(self, model_path: Optional[str] = None, seq_len: int = 50, batch_size: int = 32):
        """
        Initialize the Deep Promoter integration.
        
        Args:
            model_path: Path to a saved model or None to use default
            seq_len: Sequence length in characters
            batch_size: Batch size for generation
        """
        self.seq_len = seq_len
        self.batch_size = batch_size
        self.model_path = model_path
        
        # Set up paths
        self.cur_path = os.getcwd()
        self.data_dir = os.path.join(deep_promoter_path, 'seq')
        
        # Ensure the seq directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Set up TensorFlow session and imported modules
        self.session = None
        self.loaded = False
        self.charmap = None
        self.inv_charmap = None
        
        # Configure TensorFlow for compatibility
        self._configure_tensorflow()
    
    def _configure_tensorflow(self):
        """Configure TensorFlow for version compatibility"""
        try:
            # Enable TensorFlow 1.x compatibility mode for TensorFlow 2.x
            if hasattr(tf, 'compat') and hasattr(tf.compat, 'v1'):
                logger.info("Using TensorFlow 2.x with compatibility mode")
                tf.compat.v1.disable_eager_execution()
                tf.compat.v1.disable_v2_behavior()
                
            # Configure GPU if available
            gpus = tf.config.experimental.list_physical_devices('GPU')
            if gpus:
                for gpu in gpus:
                    tf.config.experimental.set_memory_growth(gpu, True)
                    
        except Exception as e:
            logger.warning(f"Error configuring TensorFlow: {e}")
    
    def load_model(self) -> bool:
        """
        Load the GAN model for promoter generation. Uses the original model from gan_language.py.
        
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        if self.loaded:
            return True
        
        # Model path is required
        if not self.model_path or not os.path.exists(self.model_path):
            logger.error(f"No valid model path provided: {self.model_path}")
            return False
        
        try:
            # Import the necessary modules here to avoid TensorFlow initialization conflicts
            import gan_language
            
            # Get the data structures from the Deep_promoter code
            self.charmap = gan_language.charmap
            self.inv_charmap = gan_language.inv_charmap
            
            # Create a new TensorFlow session
            if self.session:
                self.session.close()
            
            self.session = tf.compat.v1.Session()
            
            with self.session.as_default():
                # Initialize variables
                self.session.run(tf.compat.v1.global_variables_initializer())
                
                # Load the saved model using the original code's approach
                saver = tf.compat.v1.train.Saver()
                saver.restore(self.session, self.model_path)
                
                # The Generator function is used directly from the original code
                self.generator = gan_language.Generator
                
                # Mark as loaded
                self.loaded = True
                logger.info(f"Successfully loaded model from {self.model_path}")
                return True
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False
    
    def generate_promoters(self, num_sequences: int = 10) -> List[str]:
        """
        Generate new promoter sequences using the GAN model.
        
        Args:
            num_sequences: Number of promoter sequences to generate
            
        Returns:
            List of generated promoter sequences
        """
        # Try to load the model if not already loaded
        if not self.loaded:
            success = self.load_model()
            if not success:
                logger.error("Failed to load model, cannot generate sequences")
                return []
        
        try:
            # Use the original code's generate_samples method
            import gan_language
            
            if not hasattr(gan_language, 'generate_samples'):
                logger.error("Could not find generate_samples method in gan_language.py")
                return []
            
            # Run the generator for the requested number of sequences
            generated_samples = []
            while len(generated_samples) < num_sequences:
                # Call the original generate_samples method
                samples = gan_language.generate_samples()
                
                # Join tuples into strings for the specified number of sequences
                for s in samples:
                    if len(generated_samples) < num_sequences:
                        generated_samples.append(''.join(s))
            
            logger.info(f"Generated {len(generated_samples)} promoter sequences")
            return generated_samples
            
        except Exception as e:
            logger.error(f"Error generating sequences: {e}")
            return []
    
    def predict_expression(self, sequences: List[str]) -> List[float]:
        """
        Predict expression levels for a list of promoter sequences.
        
        Args:
            sequences: List of promoter sequences
            
        Returns:
            List of predicted expression levels
        """
        if not sequences:
            logger.warning("No sequences provided for expression prediction")
            return []
            
        try:
            # Save sequences to a temporary file
            temp_file = os.path.join(self.data_dir, 'temp_predicted_promoters.fa')
            with open(temp_file, 'w') as f:
                for i, seq in enumerate(sequences):
                    f.write(f">seq_{i}\n{seq}\n")
            
            # Create predictor using the original PREDICT class
            predictor = PREDICT(temp_file)
            
            # Predict expression levels
            predictor.predict()
            
            # Read the results
            results = []
            
            # Try CNN results first
            result_file = os.path.join(self.data_dir, 'seq_exp_CNN.txt')
            if os.path.exists(result_file):
                with open(result_file, 'r') as f:
                    lines = f.readlines()
                    results = [float(line.strip().split('\t')[1]) if len(line.strip().split('\t')) > 1 else 0.0 
                              for line in lines if line.strip()]
                logger.info(f"Loaded CNN prediction results for {len(results)} sequences")
                return results
            
            # Try SVR results if CNN not available
            result_file = os.path.join(self.data_dir, 'seq_exp_SVR.txt')
            if os.path.exists(result_file):
                with open(result_file, 'r') as f:
                    lines = f.readlines()
                    results = [float(line.strip().split('\t')[1]) if len(line.strip().split('\t')) > 1 else 0.0 
                              for line in lines if line.strip()]
                logger.info(f"Loaded SVR prediction results for {len(results)} sequences")
                return results
                
            logger.warning("No prediction results found")
            return []  # Return empty list if no predictions available
                
        except Exception as e:
            logger.error(f"Error predicting expression: {e}")
            return []
    
    def filter_promoters_by_expression(self, sequences: List[str], min_expression: float = 0.5) -> List[Tuple[str, float]]:
        """
        Filter promoters by their predicted expression levels.
        
        Args:
            sequences: List of promoter sequences to evaluate
            min_expression: Minimum expression level threshold
            
        Returns:
            List of tuples containing (sequence, expression_level) above the threshold
        """
        if not sequences:
            logger.warning("No sequences provided for filtering")
            return []
            
        # Get expression predictions
        expressions = self.predict_expression(sequences)
        
        if not expressions:
            logger.warning("Failed to get expression predictions for filtering")
            return []
            
        # Filter by expression level
        filtered_results = []
        for seq, expr in zip(sequences, expressions):
            if expr >= min_expression:
                filtered_results.append((seq, expr))
        
        # Sort by expression level (highest first)
        filtered_results.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Filtered to {len(filtered_results)} sequences above threshold {min_expression}")
        return filtered_results
    
    def generate_and_filter_promoters(self, num_sequences: int = 100, min_expression: float = 0.5, 
                                     return_top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Generate promoters and filter them by predicted expression level.
        
        Args:
            num_sequences: Number of sequences to generate
            min_expression: Minimum expression level to keep
            return_top_n: Number of top sequences to return
            
        Returns:
            List of tuples containing (sequence, expression_level) for the top sequences
        """
        # Generate sequences
        sequences = self.generate_promoters(num_sequences)
        
        if not sequences:
            logger.warning("Failed to generate sequences")
            return []
            
        # Filter and sort
        filtered = self.filter_promoters_by_expression(sequences, min_expression)
        
        # Return top N
        result = filtered[:return_top_n]
        logger.info(f"Returning top {len(result)} promoters by expression level")
        return result
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.session:
                self.session.close()
                self.session = None
                self.loaded = False
                logger.info("TensorFlow session cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}") 