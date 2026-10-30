"""
actions/endpoints.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from rasa_sdk.executor import ActionExecutor
from sanic import Sanic
from sanic.request import Request
from sanic.response import json as sanic_json, text as sanic_text
from actions import (
    ActionCongratFinalResults,
    ActionDynamicFaq,
    ActionFetchFinalUnitResults,
    ActionGetDynamicResponse,
    ActionGetNextDetails,
    ActionHandleDeliberationFinalResults,
    ActionHandleDynamicFinalGlobalResults,
    ActionLogFeedback,
    ActionSemanticQA,
    ActionSelectButton,
    ActionSetSession,
    ActionSetUser, ActionEvaluatorsAndPJ, ActionLangChainRouting
)
from actions.answer_from_file.answer_from_json.answer_from_json_actions import ActionGetResponseFromJSON
from actions.answer_from_file.answer_from_markdown.answer_from_langchain_grades_action import ActionAcademicStuff
from actions.answer_from_file.answer_from_pdf.answer_from_pdf_actions import ActionPGInfosFromPDF
from actions.answer_from_file.llm_helpers import HttpClientManager
from actions.context_awareness_flow.action_context_awareness import ActionMaintainConversationFlow
from actions.util_actions.common_actions import ActionUtterBotTyping
from actions.utils.services import HttpResultsService

import logging

log = logging.getLogger("rasa-actions")

# --- Setup DI : Initialize services---
dynamic_service = HttpResultsService()
results_service = HttpResultsService()
feedback_service = HttpResultsService()
dynamic_response_service = HttpResultsService()
unit_results_service = HttpResultsService()
congrat_service = HttpResultsService()
deliberation_service = HttpResultsService()
fetch_component_service = HttpResultsService()
composante_affirm_service = HttpResultsService()
semantic_qa_service = HttpResultsService()
evaluation_comps_service = HttpResultsService()
session_service = HttpResultsService()
user_service = HttpResultsService()
select_button = HttpResultsService()
next_details = HttpResultsService()
answer_from_file = HttpResultsService()

# Create executor
executor = ActionExecutor()

# Register all actions with their dependencies
# + APIS
executor.register_action(ActionDynamicFaq(dynamic_service))
executor.register_action(ActionHandleDynamicFinalGlobalResults(results_service))
executor.register_action(ActionLogFeedback(feedback_service))
executor.register_action(ActionGetDynamicResponse(dynamic_response_service))
executor.register_action(ActionFetchFinalUnitResults(unit_results_service))
executor.register_action(ActionCongratFinalResults(congrat_service))
executor.register_action(ActionSelectButton(select_button))
executor.register_action(ActionGetNextDetails(next_details))
executor.register_action(ActionHandleDeliberationFinalResults(deliberation_service))

# - APIS
executor.register_action(ActionSemanticQA(semantic_qa_service))
executor.register_action(ActionSetSession(session_service))
executor.register_action(ActionSetUser(user_service))
executor.register_action(ActionUtterBotTyping())
executor.register_action(ActionGetResponseFromJSON())
executor.register_action(ActionPGInfosFromPDF())
executor.register_action(ActionEvaluatorsAndPJ())
executor.register_action(ActionMaintainConversationFlow())
executor.register_action(ActionAcademicStuff())
executor.register_action(ActionLangChainRouting())

# --- Create Sanic app ---
app = Sanic("rasa_sdk")
app.ctx.executor = executor

# Raise Sanic middleware-level timeouts to match the Rasa endpoint timeout.
# Note: if you run behind an ingress/proxy, its own timeout may still be lower.
app.config.KEEP_ALIVE_TIMEOUT = 600
app.config.RESPONSE_TIMEOUT = 600
app.config.REQUEST_TIMEOUT = 600

# --- Define /webhook route ---
@app.post("/webhook")
async def webhook(request: Request):
    try:
        payload = request.json  # no await
        response = await executor.run(payload)
        return sanic_json(response)
    except BaseException as exc:
        # When the upstream (Rasa server / ingress) times out, it may cancel the in-flight request.
        # If this bubbles up, Sanic returns 503 and Rasa may retry the action, causing duplicates.
        if exc.__class__.__name__ == "CancelledError":
            log.warning("Webhook request cancelled by upstream; returning empty response.")
            return sanic_json([])
        raise


# --- Prometheus /metrics stub — stops the 404 log spam from the scraper ---
@app.get("/metrics")
async def metrics(request: Request):
    log.debug("Metrics requested by IP: %s", request.remote_addr)
    return sanic_text("# Rasa Action Server\n", content_type="text/plain; version=0.0.4")

# --- Graceful HTTP client shutdown ---
@app.listener("after_server_stop")
async def close_http_client(app, loop):
    await HttpClientManager.close()
    log.info("Shared HTTP client closed successfully.")

# --- Run ---
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5055,
    )

