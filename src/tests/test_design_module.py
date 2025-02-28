import unittest
import os
import json
from unittest.mock import MagicMock, patch

from src.design_module import DesignOrchestrator
from src.tools.functions import ToolIntegration
from src.library.ucf_retrieval import load_ecoli_library

class TestDesignOrchestrator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Load library data for testing
        cls.library_data = load_ecoli_library("libs/parsed/Eco1C1G1T0_parsed.json")
        cls.tool_integration = ToolIntegration(cls.library_data)
        
    def test_select_ucf_file_basic(self):
        """Test basic UCF file selection for E. coli with arabinose inducer"""
        orchestrator = DesignOrchestrator(self.tool_integration)
        
        # Test with E. coli and arabinose
        result = orchestrator.select_ucf_file(
            organism="E. coli",
            inducers=["arabinose"],
            gate_types=["NOT"]
        )
        
        # Check that a UCF file was found
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertIn("ucf_file", result)
        self.assertIn("file", result["ucf_file"])
        
        # Check that the selected UCF file has matches
        self.assertIn("matches", result["ucf_file"])
        matches = result["ucf_file"]["matches"]
        
        # Verify that we have at least one match
        self.assertTrue(len(matches) > 0, f"No matches found in the selected UCF file: {matches}")
        
        # Verify that the file name starts with Eco (for E. coli)
        file_name = result["ucf_file"]["file"]
        self.assertTrue(file_name.startswith("Eco"), f"Selected UCF file {file_name} does not start with 'Eco'")
    
    def test_select_ucf_file_with_output(self):
        """Test UCF file selection with output validation"""
        orchestrator = DesignOrchestrator(self.tool_integration)
        
        # Mock the _validate_outputs_in_ucf method to test output validation
        original_method = orchestrator._validate_outputs_in_ucf
        
        try:
            # First test with a valid output
            orchestrator._validate_outputs_in_ucf = MagicMock(return_value={"valid": True})
            
            result = orchestrator.select_ucf_file(
                organism="E. coli",
                inducers=["arabinose"],
                outputs=["GFP"],
                gate_types=["NOT"]
            )
            
            # Check that a UCF file was found and validated
            self.assertIn("success", result)
            self.assertTrue(result["success"])
            
            # Now test with an invalid output
            orchestrator._validate_outputs_in_ucf = MagicMock(return_value={
                "valid": False,
                "missing": ["GFP"]
            })
            
            result = orchestrator.select_ucf_file(
                organism="E. coli",
                inducers=["arabinose"],
                outputs=["GFP"],
                gate_types=["NOT"]
            )
            
            # Check that a warning was returned
            self.assertIn("warning", result)
            self.assertIn("recommendation", result)
            self.assertIn("ucf_file", result)
        finally:
            # Restore the original method
            orchestrator._validate_outputs_in_ucf = original_method
    
    def test_design_circuit(self):
        """Test circuit design with UCF file selection"""
        orchestrator = DesignOrchestrator(self.tool_integration)
        
        # Mock the select_ucf_file method to return a known UCF file
        orchestrator.select_ucf_file = MagicMock(return_value={
            "success": True,
            "ucf_file": {
                "file": "Eco1C1G1T1.UCF.json",
                "path": "ext_repos/Cello-UCF/files/v2/ucf/Eco/Eco1C1G1T1.UCF.json",
                "matches": {"arabinose": 5, "AraC": 10, "NOT": 3}
            }
        })
        
        # Mock the design_with_cello_func method to return a success result
        orchestrator.tools.design_with_cello_func = MagicMock(return_value={
            "success": True,
            "dna_design": {"sequence": "ATGC..."},
            "log": "Cello design successful"
        })
        
        # Test designing a NOT gate circuit
        verilog_code = """
        module NOT_gate (input a, output out);
            assign out = ~a;
        endmodule
        """
        
        result = orchestrator.design_circuit(
            verilog_code=verilog_code,
            organism="E. coli",
            inducers=["arabinose"],
            outputs=["GFP"],
            gate_types=["NOT"]
        )
        
        # Check that the circuit was designed successfully
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertIn("dna_design", result)
        self.assertIn("ucf_file", result)
        self.assertEqual(result["ucf_file"], "Eco1C1G1T1.UCF.json")
        
        # Verify that the select_ucf_file method was called with the correct arguments
        orchestrator.select_ucf_file.assert_called_once_with(
            "E. coli",
            ["arabinose"],
            ["GFP"],
            ["NOT"]
        )
        
        # Verify that the design_with_cello_func method was called with the correct arguments
        orchestrator.tools.design_with_cello_func.assert_called_once()
        args, kwargs = orchestrator.tools.design_with_cello_func.call_args
        self.assertEqual(args[0], verilog_code)
        self.assertIn("ucf_name", args[1])

    @patch('openai.OpenAI')
    def test_design_circuit_with_llm(self, mock_openai):
        """Test circuit design with LLM-based UCF file selection"""
        # Mock the OpenAI client and response
        mock_client = mock_openai.return_value
        mock_chat = mock_client.chat
        mock_completions = mock_chat.completions
        mock_create = mock_completions.create
        
        # Create a mock response object
        class MockResponse:
            class MockChoice:
                class MockMessage:
                    def __init__(self, content):
                        self.content = content
                
                def __init__(self, content):
                    self.message = self.MockMessage(content)
            
            def __init__(self, content):
                self.choices = [self.MockChoice(content)]
        
        # Set the return value for the create method
        mock_create.return_value = MockResponse(
            "REASONING: Based on the user request for a NOT gate circuit in E. coli with GFP output and arabinose sensing, "
            "I recommend the Eco2C2G2T2 library because it supports E. coli and has the necessary components.\n"
            "SELECTED_LIBRARY: Eco2C2G2T2"
        )
        
        orchestrator = DesignOrchestrator(self.tool_integration)
    
        # Mock the llm_select_ucf_func method to return a known UCF file
        orchestrator.tools.llm_select_ucf_func = MagicMock(return_value={
            "success": True,
            "library_id": "Eco2C2G2T2",
            "message": "Selected library Eco2C2G2T2 based on LLM reasoning",
            "metadata": {
                "library_id": "Eco2C2G2T2",
                "part_count": 4,
                "gate_count": 6,
                "gate_types": ["nor"],
                "has_reporters": {"gfp": False, "rfp": False, "yfp": False, "cfp": False},
                "has_inducers": {"arabinose": False, "iptg": False, "atc": False, "hsl": False},
                "organism": "E. coli"
            }
        })
    
        # Mock the design_with_cello_func method to return a success result
        orchestrator.tools.design_with_cello_func = MagicMock(return_value={
            "success": True,
            "dna_design": {"sequence": "ATGC..."},
            "log": "Cello design successful"
        })
    
        # Test designing a NOT gate circuit with LLM-based UCF selection
        verilog_code = """
        module NOT_gate (input a, output out);
            assign out = ~a;
        endmodule
        """
        
        user_request = "I want to design a NOT gate circuit for E. coli that produces GFP when arabinose is absent."
    
        # Test without providing llm_reasoning (should call the LLM)
        result = orchestrator.design_circuit(
            verilog_code=verilog_code,
            user_request=user_request,
            use_llm=True
        )
    
        # Check that the circuit was designed successfully
        self.assertIn("success", result)
        self.assertTrue(result["success"])
        self.assertIn("dna_design", result)
        self.assertIn("ucf_file", result)
        self.assertEqual(result["ucf_file"], "Eco2C2G2T2.UCF.json")
        self.assertIn("library_id", result)
        self.assertEqual(result["library_id"], "Eco2C2G2T2")
    
        # Verify that the OpenAI API was called
        mock_create.assert_called_once()
        
        # Verify that the llm_select_ucf_func method was called
        orchestrator.tools.llm_select_ucf_func.assert_called_once()
    
        # Verify that the design_with_cello_func method was called with the correct arguments
        orchestrator.tools.design_with_cello_func.assert_called_once()
        args, kwargs = orchestrator.tools.design_with_cello_func.call_args
        self.assertEqual(args[0], verilog_code)
        self.assertIn("ucf_name", args[1])
        self.assertEqual(args[1]["ucf_name"], "Eco2C2G2T2.UCF.json")

if __name__ == "__main__":
    unittest.main() 