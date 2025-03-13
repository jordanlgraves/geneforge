import unittest
import os
from src.library.llm_library_selector import RuleBasedLibrarySelector, LLMBasedLibrarySelector
from src.library.library_manager import LibraryManager

class TestRuleBasedLibrarySelector(unittest.TestCase):
    """
    Tests for the RuleBasedLibrarySelector class.
    These tests verify that the rule-based selector can correctly analyze user requests and select appropriate libraries.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Create a library manager for testing
        cls.library_manager = LibraryManager()
        
        # Get available libraries for testing
        cls.available_libraries = cls.library_manager.get_available_libraries()
            
        print(f"Available libraries for testing: {cls.available_libraries}")
        
        # Create a library selector
        cls.library_selector = RuleBasedLibrarySelector(cls.library_manager)
    
    def test_analyze_user_request(self):
        """Test that the library selector can analyze user requests correctly"""
        # Test with a simple request
        request = "I want to design a circuit for E. coli with GFP output"
        analysis = self.library_selector.analyze_user_request(request)
        
        # Check that the analysis contains the expected fields
        self.assertIn("organisms", analysis)
        self.assertIn("parts", analysis)
        self.assertIn("gates", analysis)
        self.assertIn("reporters", analysis)
        self.assertIn("inducers", analysis)
        self.assertIn("raw_request", analysis)
        
        # Check that the analysis correctly identified the organism and reporter
        self.assertIn("e. coli", analysis["organisms"])
        self.assertIn("gfp", analysis["reporters"])
        
        # Test with a more complex request
        request = "I need a genetic circuit for yeast that uses a NOT gate with RFP output and IPTG induction"
        analysis = self.library_selector.analyze_user_request(request)
        
        # Check that the analysis correctly identified all components
        self.assertIn("yeast", analysis["organisms"])
        self.assertIn("not", analysis["gates"])
        self.assertIn("rfp", analysis["reporters"])
        self.assertIn("iptg", analysis["inducers"])
    
    def test_select_library(self):
        """Test that the library selector can select appropriate libraries"""
        # Test with a simple request for E. coli
        request = "I want to design a circuit for E. coli"
        result = self.library_selector.select_library(request)
        
        # Check that a library was selected
        self.assertTrue(result["success"])
        self.assertIn("library_id", result)
        self.assertIn("message", result)
        
        # Check that the selected library is for E. coli
        self.assertTrue(result["library_id"].startswith("Eco"))
        
        # Test with a request for yeast (if available)
        has_yeast = any(lib.startswith("SC") for lib in self.available_libraries)
        if has_yeast:
            request = "I want to design a circuit for yeast"
            result = self.library_selector.select_library(request)
            
            # Check that a library was selected
            self.assertTrue(result["success"])
            self.assertIn("library_id", result)
            
            # Check that the selected library is for yeast
            self.assertTrue(result["library_id"].startswith("SC"))
        
        # Test with a request for an unavailable organism
        request = "I want to design a circuit for Pseudomonas aeruginosa"
        result = self.library_selector.select_library(request)
        
        # Check that a library was still selected (should default to E. coli)
        self.assertTrue(result["success"])
        self.assertIn("library_id", result)
        
        # The message should indicate that no specific organism was identified
        self.assertIn("No specific organism was identified", result["message"])
    
    def test_get_library_metadata(self):
        """Test that the library selector can retrieve library metadata"""
        # Get metadata for the first available library
        library_id = self.available_libraries[0]
        metadata = self.library_selector.get_library_metadata(library_id)
        
        # Check that the metadata contains the expected fields
        self.assertIn("library_id", metadata)
        self.assertIn("part_count", metadata)
        self.assertIn("gate_count", metadata)
        self.assertIn("gate_types", metadata)
        self.assertIn("has_reporters", metadata)
        self.assertIn("has_inducers", metadata)
        self.assertIn("organism", metadata)
        
        # Check that the library ID matches
        self.assertEqual(metadata["library_id"], library_id)
        
        # Check that the part and gate counts are non-negative
        self.assertGreaterEqual(metadata["part_count"], 0)
        self.assertGreaterEqual(metadata["gate_count"], 0)
    
    def test_missing_features(self):
        """Test that the library selector correctly identifies missing features"""
        # Test with a request for features that might not be available
        request = "I want to design a circuit for E. coli with XOR gates and CFP output"
        result = self.library_selector.select_library(request)
        
        # Check if any features are missing
        if "missing_features" in result and result["missing_features"]:
            # Print the missing features for debugging
            print(f"Missing features: {result['missing_features']}")
            
            # Check that the missing features are correctly identified
            for feature in result["missing_features"]:
                self.assertTrue(
                    "xor gate" in feature.lower() or "cfp reporter" in feature.lower() or
                    "and gate" in feature.lower() or "library_data_unavailable" in feature.lower()
                )
    
    def test_alternative_libraries(self):
        """Test that the library selector can find alternative libraries"""
        # Test with a request that might have alternatives
        request = "I want to design a circuit for E. coli with GFP output"
        result = self.library_selector.select_library(request)
        
        # Check that alternatives were provided
        self.assertIn("alternatives", result)
        
        # If there are multiple libraries, there should be alternatives
        if len(self.available_libraries) > 1:
            self.assertTrue(len(result["alternatives"]) > 0)
            
            # Check that each alternative has the required fields
            for alternative in result["alternatives"]:
                self.assertIn("library_id", alternative)
                self.assertIn("missing_features", alternative)


class TestLLMBasedLibrarySelector(unittest.TestCase):
    """
    Tests for the LLMBasedLibrarySelector class.
    These tests verify that the LLM-based selector can correctly analyze user requests and select appropriate libraries.
    Note: These tests require a valid OpenAI API key to be set in the environment.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Check if OpenAI API key is available
        # Create a library manager for testing
        cls.library_manager = LibraryManager()
        
        # Get available libraries for testing
        cls.available_libraries = cls.library_manager.get_available_libraries()
        
        print(f"Available libraries for testing: {cls.available_libraries}")
        
        # Create a library selector
        cls.library_selector = LLMBasedLibrarySelector(cls.library_manager)
    
    def test_select_library(self):
        """Test that the LLM-based library selector can select appropriate libraries"""
        # Test with a simple request for E. coli
        request = "I want to design a circuit for E. coli"
        result = self.library_selector.select_library(request)
        
        # Check that a library was selected
        self.assertTrue(result["success"])
        self.assertIn("library_id", result)
        self.assertIn("message", result)
        self.assertIn("reasoning", result)
        
        # Check that the selected library is for E. coli
        self.assertTrue(result["library_id"].startswith("Eco"))
        
        # Test with a more detailed request
        request = "I want to design a circuit for E. coli with GFP output and arabinose induction"
        result = self.library_selector.select_library(request)
        
        # Check that a library was selected
        self.assertTrue(result["success"])
        self.assertIn("library_id", result)
        self.assertIn("reasoning", result)
        
        # The reasoning should mention output/reporter and inducer terms
        # Using more flexible matching to accommodate different LLM phrasings
        output_terms = ["gfp", "green fluorescent protein", "fluorescent", "output", "reporter"]
        inducer_terms = ["arabinose", "induction", "inducer", "input"]
        
        self.assertTrue(any(term in result["reasoning"].lower() for term in output_terms), 
                       f"Reasoning doesn't mention any output terms: {result['reasoning']}")
        self.assertTrue(any(term in result["reasoning"].lower() for term in inducer_terms),
                       f"Reasoning doesn't mention any inducer terms: {result['reasoning']}")
    
    def test_no_matching_library(self):
        """Test that the LLM-based library selector handles cases with no matching library"""
        # Test with a request for an organism that doesn't exist in our libraries
        request = "I want to design a circuit for Deinococcus radiodurans with blue-light sensing"
        result = self.library_selector.select_library(request)
        
        # Check the response
        self.assertIn("success", result)
        self.assertIn("recommendations", result)
        self.assertEqual(result['success'], False)
        self.assertIsNone(result.get('library_id', None))
        # The response should include an explanation about why no matching library was found
        self.assertTrue(len(result["recommendations"]) > 0)
    
    def test_get_library_metadata(self):
        """Test that the LLM-based library selector can retrieve library metadata"""
        # Get metadata for the first available library
        library_id = self.available_libraries[0]
        metadata = self.library_selector.get_library_metadata(library_id)
        
        # Check that the metadata contains the expected fields
        self.assertIn("library_id", metadata)
        self.assertIn("organism", metadata)
        
        # Check that the library ID matches
        self.assertEqual(metadata["library_id"], library_id)


if __name__ == "__main__":
    unittest.main() 