"""
actions/utils/exception_error_messages.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.constants.Constants import FEEDBACK_BUTTONS, BOT_MESSAGES
from actions.utils.message_helpers import send_custom_fallback_problem_to_dsi_forwarded_by_buttons, get_random_message

def exception_llm_err(dispatcher):
    answer = "😢 Désolé, je n'ai pas réussi à générer la réponse. \nPeux-tu reformuler ? 🙏"
    dispatcher.utter_message(answer)
    return answer

def exception_fallback_err(dispatcher):
    answer = "😕 Oups… une erreur de réseau est survenue. \nRéessaye dans un instant 🙏"
    dispatcher.utter_message(answer)

def exception_llm_err_dsi(dispatcher, action_label, payload_tech_error, llm_err_str):
    answer_exception = "💥 Fatal LLM Error: "
    send_custom_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, str(llm_err_str), answer_exception, FEEDBACK_BUTTONS)

def exception_fallback_err_dsi(dispatcher, action_label, payload_tech_error, fallback_err_str):
    answer_exception = "❌ Fallback LLM also failed: "
    send_custom_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, str(fallback_err_str), answer_exception, FEEDBACK_BUTTONS)

def unexpected_exception_dsi(dispatcher, action_label, payload_tech_error, unexpected_str):
    answer_exception = get_random_message(BOT_MESSAGES['fallback_dsi'])
    reply_exception = send_custom_fallback_problem_to_dsi_forwarded_by_buttons(dispatcher, action_label, payload_tech_error, unexpected_str, answer_exception, FEEDBACK_BUTTONS)
    return reply_exception