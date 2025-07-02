import unittest
import json
from pathlib import Path
import sys
import os

# Ensure project root is on PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import pytest

from src.library import cello_utils
from src.session_state import SessionState
from src.tools.promoter_tools import (
    AddPromoterVariantTool,
    RemovePromoterTool,
)

TEST_UCF = Path("ext_repos/Cello-UCF/files/v2/ucf/Eco/Eco2C1G3T1.UCF.json")


@pytest.fixture(scope="module")
def eco_ucf_data():
    with TEST_UCF.open() as f:
        return json.load(f)


def test_duplicate_promoter_dependencies(eco_ucf_data):
    parent = "pPhlF"
    new_name = f"{parent}_var1"
    seq = "CGACGTACGGTGGAATTTTTTTTTTTTTTTTTTT"  #  placeholder
    y_max = 0.0

    new_items, gate_map = cello_utils.duplicate_promoter_dependencies(
        eco_ucf_data, parent, new_name, seq, y_max
    )

    # ---- sanity checks
    assert any(p["collection"] == "parts" and p["name"] == new_name for p in new_items)
    assert any(
        s["collection"] == "structures" and parent not in s["name"]
        for s in new_items
        if s["collection"] == "structures"
    )
    assert gate_map, "expected at least one duplicated gate"

# unit test
class TestPromoterVariantTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session_state = SessionState()
        cello_library = cls.session_state.cello_library
        eco_libs = [lib for lib in cello_library.get_available_libraries() if "Eco" in lib]
        if not eco_libs:
            raise RuntimeError("No E.coli libraries found for testing")
        cello_library.select_library(eco_libs[0])
        cls.cello_library = cello_library

    def test_add_promoter_variant(self):
        ucf_before = self.cello_library.user_constrains
        parent_promoter = cello_utils.get_parts_by_type(ucf_before, "promoter")[0]
        parent_id = parent_promoter["name"]

        tool = AddPromoterVariantTool(self.session_state)
        result = tool.execute(
            parent_promoter_id=parent_id,
            spacer_sequence="A" * 17,
            ymax=2.5,
        )
        assert result["success"], result.get("error", "")
        custom_path = Path(self.session_state.cello_library.user_constraints_path)
        assert custom_path.exists()

        # verify new promoter exists with correct parameters
        with custom_path.open() as f:
            ucf_data = json.load(f)
        new_promoter = cello_utils.get_part_by_name(ucf_data, result["new_promoter_id"])
        assert new_promoter is not None
        # confirm sequence includes spacer string
        assert "A" * 17 in (new_promoter.get("dnasequence") or new_promoter.get("sequence"))

        # model updated
        related_models = [
            m
            for m in ucf_data
            if m.get("collection") == "models" and result["new_promoter_id"].replace("p", "") in m.get("name")
        ]
        assert related_models, "expected duplicated model entries"
        has_ymax = any(
            any(p.get("name").lower() in ("ymax", "y_max") and float(p["value"]) == 2.5 for p in m.get("parameters", []))
            for m in related_models
        )
        assert has_ymax, "duplicated models should carry new ymax"

    def test_remove_promoter(self):
        # Use the custom UCF created previously
        custom_ucf_path = self.session_state.cello_library.user_constraints_path
        assert custom_ucf_path, "Previous step should have produced custom UCF"
        # Load custom library in manager
        self.cello_library.user_constraints_path = custom_ucf_path
        self.cello_library.user_constrains = json.loads(Path(custom_ucf_path).read_text())

        # Remove the variant promoter
        promoters = cello_utils.get_parts_by_type(
            self.cello_library.user_constrains, "promoter"
        )
        variant_promoters = [p for p in promoters if p["name"].endswith("var1")]
        assert variant_promoters, "No promoter variant ending with 'var1' found"
        variant_id = variant_promoters[0]["name"]
        remover = RemovePromoterTool(self.session_state)
        out = remover.execute(promoter_id=variant_id)
        assert out["success"], out.get("error", "")
        path_after = Path(self.session_state.cello_library.user_constraints_path)
        data_after = json.loads(path_after.read_text())
        assert cello_utils.get_part_by_name(data_after, variant_id) is None, "Promoter variant should be removed"

if __name__ == "__main__":
    unittest.main()