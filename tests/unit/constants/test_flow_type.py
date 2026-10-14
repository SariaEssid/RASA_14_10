"""
tests/unit/test_flow_type.py

@author ESSID Saria | Copyright (c) 2026. ESPRIT
"""

import pytest
from actions.constants.FlowType import FlowType, SSCOMP_TO_FLOW, INTENT_TO_FLOW


# =========================================================
# TEST FLOWTYPE ENUM BEHAVIOR
# =========================================================

def test_flow_type_string_conversion():
    """Ensure that converting a FlowType enum to a string returns its value."""
    assert str(FlowType.NOTE_FIRST_COMP) == "note_first_comp"
    assert str(FlowType.EVALUATION_GRID) == "eval_grid"
    assert str(FlowType.DUMMY_FLOW) == "dummy_flow"


def test_flow_type_inheritance():
    """Ensure FlowType inherits correctly from str and Enum."""
    assert isinstance(FlowType.GREET, str)
    assert FlowType.BYE == "bye"


# =========================================================
# TEST SSCOMP_TO_FLOW MAPPINGS
# =========================================================

@pytest.mark.parametrize(
    "sscomp_key, expected_flow",
    [
        ("first_comp", FlowType.NOTE_FIRST_COMP),
        ("second_comp", FlowType.NOTE_SECOND_COMP),
        ("third_comp", FlowType.NOTE_THIRD_COMP),
        ("test_qcm", FlowType.NOTE_TEST_QCM),
        ("eval_pres_se", FlowType.NOTE_EVAL_PRES_SE),
        ("entr_jury_all", FlowType.NOTE_ENTR_JURY_ALL),
    ],
)
def test_sscomp_to_flow_valid_mappings(sscomp_key, expected_flow):
    """Verify that specific sub-components map to the correct FlowType."""
    assert SSCOMP_TO_FLOW[sscomp_key] == expected_flow


def test_sscomp_to_flow_total_count():
    """Ensure all declared elements in SSCOMP_TO_FLOW are accounted for."""
    assert len(SSCOMP_TO_FLOW) == 20


# =========================================================
# TEST INTENT_TO_FLOW MAPPINGS
# =========================================================

@pytest.mark.parametrize(
    "intent_key, expected_flow",
    [
        ("ask_about_candidature_passage_grade", FlowType.GUIDE_COMP),
        ("stressed_candidat", FlowType.SELECTED_ADVICE_PLAN),
        ("select_comp_for_guide", FlowType.SELECTED_COMP),
        ("affirm_advice_1", FlowType.GIVE_ADVICE_1),
        ("affirm_advice_2", FlowType.GIVE_ADVICE_2),
        ("affirm_advice_3", FlowType.GIVE_ADVICE_3),
        ("ask_criteres_evaluation_sscomp", FlowType.EVALUATION_GRID),
    ],
)
def test_intent_to_flow_valid_mappings(intent_key, expected_flow):
    """Verify that incoming Rasa intents route to the correct business flows."""
    assert INTENT_TO_FLOW[intent_key] == expected_flow


def test_intent_to_flow_total_count():
    """Ensure all declared intents in INTENT_TO_FLOW are present."""
    assert len(INTENT_TO_FLOW) == 7