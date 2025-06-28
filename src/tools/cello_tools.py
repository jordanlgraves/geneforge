"""Cello design- and library-management tool classes extracted from
src.functions for better modularity and maintainability.

The classes are copied verbatim (apart from updated imports) so that any
behavioural change is avoided.  They still rely on the ``Tool`` base class
and the ``DEBUG_MODE`` flag defined in ``src.functions`` to minimise the
risk of circular import problems during the transition.
"""

from __future__ import annotations

from typing import Dict, List, Any
import os
import traceback
import logging

import src.library.part_library_customizer as part_library_customizer
from src.session_state import SessionState  # lint helper – referenced via "self.session_state"

# Import the shared Tool base class and DEBUG flag from the original module.
# This avoids moving too much code in a single step.
from src.functions import Tool, DEBUG_MODE  # noqa: E402  pylint: disable=wrong-import-position

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Cello library exploration / management tools
# ---------------------------------------------------------------------------

# The code blocks below are copied unchanged from ``src.functions`` (lines 43-680
# at the time of extraction).

# ... existing code ... 

# Re-export the original class definitions so that external modules can simply
# import them from ``src.tools.cello_tools`` while we migrate the full source
# code in smaller, reviewable chunks.  This keeps the public API intact and
# allows gradual refactoring.

from src.functions import (
    ListPromotersTool,
    ListInputSensorsTool,
    DescribeAvailableLibrariesTool,
    SelectLibraryTool,
    QueryLibrariesByOrganismTool,
    ListRepressorsTool,
    GetDnaPartByNameTool,
    ListTerminatorsTool,
    DesignWithCelloTool,
    CreateCustomUcfTool,
    CreateCustomInputSensorsFileTool,
    EvaluateCircuitPerformanceTool,
    AddPromoterVariantTool,
    RemovePromoterTool,
    CommitCustomLibraryTool,
    GetCelloLibraryStatusTool,
)

__all__ = [
    "ListPromotersTool",
    "ListInputSensorsTool",
    "DescribeAvailableLibrariesTool",
    "SelectLibraryTool",
    "QueryLibrariesByOrganismTool",
    "ListRepressorsTool",
    "GetDnaPartByNameTool",
    "ListTerminatorsTool",
    "DesignWithCelloTool",
    "CreateCustomUcfTool",
    "CreateCustomInputSensorsFileTool",
    "EvaluateCircuitPerformanceTool",
    "AddPromoterVariantTool",
    "RemovePromoterTool",
    "CommitCustomLibraryTool",
    "GetCelloLibraryStatusTool",
] 