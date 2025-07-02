import unittest
import tellurium as te
import libsbml
from src.integrations.kinmod_gpt_integration import KineticModelingGPTIntegration
from src.simulate.param_template import build_param_template

class TestKineticModelIntegration(unittest.TestCase):
    """
    Tests for the library selection functionality.
    These tests verify that the system can correctly select libraries based on user input.
    """
    def setUp(self):
        self.gpt = KineticModelingGPTIntegration()

    def test_generate_model(self):
        """Test filtering libraries by organism"""
        # Test filtering by organism
        spec = "Gene A produces protein A, which activates Gene B. Gene B produces protein B, which activates Gene A. Both proteins degrade at a rate k_deg. The output (GFP) is produced by Gene A. The ON inducer activates Gene A, and the OFF inducer inhibits Gene B. Initial concentrations: [A] = 0, [B] = 0, [ON] = 0, [OFF] = 0. The ON inducer is turned up at time 50, the OFF inducer is turned up at time 150."
        antimony, messages = self.gpt.generate_kinetic_model(spec)

        sbml_xml = te.antimonyToSBML(antimony)
        sbml_doc = libsbml.readSBMLFromString(sbml_xml)

        sbml_str = libsbml.writeSBMLToString(sbml_doc)
        rr = te.loadSBMLModel(sbml_str)

        template = build_param_template(sbml_doc)
        self.assertIsNotNone(template, "Should be able to build a parameter template")

if __name__ == "__main__":
    unittest.main() 