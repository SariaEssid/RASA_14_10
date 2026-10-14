"""
actions/constants/ActionsLabel.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from enum import Enum

class ActionsNome(str, Enum):
    ACTION_PG_INFOS_PDF = "action_pg_infos_pdf"
    ACTION_LANG_CHAIN_ROUTING = "action_lang_chain_routing"
    ACTION_EVALUATORS_PJS = "action_evaluators_pjs"
    ACTION_GET_RESPONSE_FROM_JSON = "action_get_response_from_json"
    ACTION_ACADEMIC_STUFF = "action_academic_stuff"
    ACTION_MAINTAIN_CONV_FLOW = "action_maintain_conv_flow"
    ACTION_SELECT_BUTTON = "action_select_button"
    ACTION_SET_SESSION = "action_set_session"
    ACTION_SET_USER = "action_set_user"
    ACTION_LOG_FEEDBACK = "action_log_feedback"
    ACTION_GET_DYNAMIC_RESPONSE = "action_get_dynamic_response"
    ACTION_GET_NEXT_DETAILS_RESPONSE = "action_get_next_details_response"
    ACTION_DYNAMIC_FINAL_UNIT_RESULTS = "action_dynamic_final_unit_results"
    ACTION_CONGRAT_FINAL_RESULTS = "action_congrat_final_results"
    ACTION_DYNAMIC_FAQ = "action_dynamic_faq"
    ACTION_BILAN_FINAL_RESULTS = "action_bilan_final_results"
    ACTION_DELIBERATION_FINAL_RESULTS = "action_deliberation_final_results"
    ACTION_SEMANTIC_QA = "action_semantic_qa"
    ACTION_BOT_TYPING = "action_bot_typing"

    def __str__(self):
        return self.value