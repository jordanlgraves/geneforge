import os
import sys
import unittest
import dotenv

dotenv.load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.session_state import SessionState
from src.functions import ConvertSbolToSbmlTool


class TestToolConvertSBMLTool(unittest.TestCase):
    """Tests the behaviour of TestToolConvertSBML.

    These tests perform live queries against the OpenAI assistants API, which
    requires a valid OPENAI_API_KEY to be set in the environment.
    """

    @classmethod
    def setUpClass(cls):
        """Initialise a single session state for all tests."""
        cls.session_state = SessionState()
        cls.tool = ConvertSbolToSbmlTool(cls.session_state)

    # def test_convert_sbol_to_sbml(self):
    #     out = self.tool.execute(sbol_path="notebooks/sbol_to_sbml/GeneticToggleSwitch/GeneticToggleSwitch.rdf")

    #     self.assertTrue(out.get("success"))

    def test_convert_sbol_to_sbml2(self):
        sbol_path = "outputs/cello_run/not_gate_design/output/main.v/main.v_ucf._pySBOL3.nt"
        # # Convert nt to xml
        from sbol_utilities import conversion
        import sbol3

        # doc = sbol3.Document()
        # doc.read(sbol_path, file_format="xml")
        # print('--------------------------------')
        # print("Original SBOL-3 (nt) document read with sbol3: main.v_ucf._pySBOL3.nt")
        # print(doc.summary())
        # print('--------------------------------')
        
        # doc2 = conversion.convert3to2(doc)
        # print('--------------------------------')
        # print("Converted SBOL-3 document (nt to xml) w/ sbol_utilities.conversion.convert3to2: main.v_ucf._pySBOL3_convert3to2.rdf")
        # print(doc2.summary())
        # doc2.write("outputs/cello_run/not_gate_design/output/main.v/main.v_ucf._pySBOL3_convert3to2.rdf")        

        import sbol2
        # out_sanity = self.tool.execute(sbol_path="notebooks/sbol_to_sbml/reference_sbol2sbml/GeneticToggleSwitch.rdf")
        # doc2_sanity = sbol2.Document()
        # doc2_sanity.read("notebooks/sbol_to_sbml/reference_sbol2sbml/GeneticToggleSwitch.rdf")
        # print('--------------------------------')
        # print("Reference SBOL-2 document: GeneticToggleSwitch.rdf")
        # print(doc2_sanity.summary())    
        # doc3_sanity = sbol3.Document()
        # doc3_sanity.read("notebooks/sbol_to_sbml/reference_sbol2sbml/GeneticToggleSwitch.rdf")
        # print('--------------------------------')
        # print("Reference SBOL-3 document: GeneticToggleSwitch.rdf")
        # print(doc3_sanity.summary())
        
        sbol_prepared_path = "/Users/admin/repos/geneforge/outputs/cello_run/not_gate_design/output/main.v/main.v_ucf._pySBOL3_pysbol2_prepared.rdf"# sbol_path.replace("main.v_ucf._pySBOL3.nt", "main.v_ucf._pySBOL3_pysbol2_prepared.rdf")
        # from src.convert import SBOL2SBMLConverter
        # SBOL2SBMLConverter.prepare_sbol3_for_sbml(sbol_path, sbol_prepared_path)

        # prepped_doc2 = sbol2.Document()
        # prepped_doc2.read(sbol_prepared_path)
        # print('--------------------------------')
        # print("Prepared document read w/ sbol2: main.v_ucf._pySBOL3_pysbol2_prepared.rdf")
        # print(prepped_doc2.summary())   

        # prepped_doc3 = sbol3.Document()
        # prepped_doc3.read(sbol_prepared_path)
        # print('--------------------------------')
        # print("Prepared document read w/ sbol3: main.v_ucf._pySBOL3_pysbol2_prepared.rdf")
        # print(prepped_doc3.summary())

        out = self.tool.execute(sbol_path=sbol_prepared_path)
        self.assertTrue(out.get("success"))

    



if __name__ == "__main__":
    unittest.main(verbosity=2)
