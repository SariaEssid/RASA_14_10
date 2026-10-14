"""
tests/unit/test_suite.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.actions import clean_llm_response
from actions.utils.slots_helpers import get_return_slots_authentication
from tests.utils.constants import USER_1_ROLES, USER_1_FULL_NAME, USER_1_ID, USER_1_TOKEN

# 1. Test Slot Logic (High Coverage for Auth Flow)
def test_authentication_slots():
    roles = USER_1_ROLES
    jwt = USER_1_TOKEN
    id_candidat = USER_1_ID
    full_name = USER_1_FULL_NAME

    result = get_return_slots_authentication(jwt, roles, id_candidat, full_name)

    assert len(result) > 0
    assert any(s.get("name") == "jwt" and s.get("value") == jwt for s in result)

# 2. Test Text Processing (High Coverage for RAG cleanup)
def test_clean_llm_response_formatting():
    raw_text = "Hello.\n\n\nHow can I help?\n\n"
    cleaned = clean_llm_response(raw_text)
    # Ensure no triple newlines exist
    assert "\n\n\n" not in cleaned
    assert cleaned.strip() == "Hello.\nHow can I help?"