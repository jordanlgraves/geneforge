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

from src.library import part_library_customizer as plc
from src.library.library_manager import LibraryManager, _read_cello_config_file
from src.session_state import SessionState
from src.tools.functions import (
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

    new_items, gate_map = plc.duplicate_promoter_dependencies(
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
        lm = cls.session_state.get_library_manager()
        eco_libs = [lib for lib in lm.get_available_libraries() if "Eco" in lib]
        if not eco_libs:
            raise RuntimeError("No E.coli libraries found for testing")
        lm.select_library(eco_libs[0])
        cls.library_manager = lm

    def test_add_promoter_variant(self):
        ucf_before = self.library_manager.get_ucf_data()
        parent_promoter = plc.get_parts_by_type(ucf_before, "promoter")[0]
        parent_id = parent_promoter["name"]

        tool = AddPromoterVariantTool(self.session_state)
        result = tool.execute(
            parent_promoter_id=parent_id,
            spacer="A" * 17,
            ymax=2.5,
        )
        assert result["success"], result.get("error", "")
        custom_path = Path(result["custom_ucf_path"])
        assert custom_path.exists()

        # verify new promoter exists with correct parameters
        with custom_path.open() as f:
            ucf_data = json.load(f)
        new_promoter = plc.get_part_by_name(ucf_data, result["new_promoter_id"])
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
        custom_ucf_path = self.session_state.custom_ucf_path
        assert custom_ucf_path, "Previous step should have produced custom UCF"
        # Load custom library in manager
        self.library_manager.current_ucf_path = custom_ucf_path
        self.library_manager.current_ucf_data = json.loads(Path(custom_ucf_path).read_text())

        # Remove the variant promoter
        variant_id = [p for p in plc.get_parts_by_type(self.library_manager.get_ucf_data(), "promoter") if p["name"].endswith("var1")][0]["name"]
        remover = RemovePromoterTool(self.session_state)
        out = remover.execute(promoter_id=variant_id)
        assert out["success"], out.get("error", "")
        path_after = Path(out["custom_ucf_path"])
        data_after = json.loads(path_after.read_text())
        assert plc.get_part_by_name(data_after, variant_id) is None, "Promoter variant should be removed"

if __name__ == "__main__":
    unittest.main()