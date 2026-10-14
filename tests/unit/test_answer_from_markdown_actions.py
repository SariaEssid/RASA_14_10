"""
tests/unit/test_answer_from_markdown_actions.py

@author ESSID Saria
"""
from typing import Any

from actions.answer_from_file.answer_from_markdown.answer_from_markdown_actions import (
    format_values,
    detect_domain,
    get_academic_stuff_rules,
    get_native_question_domain_nbr_chunks, search_expert_all_roles, get_infos_by_expert_name,
    get_comp_values_from_synonyms, get_decision_mode, ActionLangChainRouting,
    ActionAcademicStuff, ActionEvaluatorsAndPJ
)
from actions.answer_from_file.llm_helpers import skip_duplication
from actions.constants.ActionsLabel import ActionsLabel

from actions.constants.ActiveIntents import ActiveIntents

import pytest
from unittest.mock import AsyncMock, Mock

# =========================================================
# format_values
# =========================================================

def test_format_values_single():
    result = format_values("john")

    assert result == "```JOHN```"


def test_format_values_multiple():
    result = format_values("john, alice, bob")

    assert result == "```JOHN```, ```ALICE```, ```BOB```"


def test_format_values_with_spaces():
    result = format_values("  john  ,   alice ")

    assert result == "```JOHN```, ```ALICE```"

# =========================================================
# detect_domain
# =========================================================

def test_detect_domain_formateur():
    result = detect_domain("comment devenir formateur")

    assert result == ["ef"]

def test_detect_domain_technologue():
    result = detect_domain("grade technologue")

    assert result == ["ef"]


def test_detect_domain_langue():
    result = detect_domain("specialite langue")

    assert result == ["elcc"]


def test_detect_domain_agrege():
    result = detect_domain("Enseignant Formateur")

    assert result == ["ef"]


def test_detect_domain_procedure_excluded():
    result = detect_domain("procedure technologue")

    assert result == []


def test_detect_domain_unknown():
    result = detect_domain("hello world")

    assert result == []


# =========================================================
# get_academic_stuff_rules
# =========================================================

def test_get_academic_stuff_rules_contains_expected_values():
    result = get_academic_stuff_rules()

    assert "Technologie de l'information" in result
    assert "Langues et Communications" in result
    assert "jamais postuler" in result


# =========================================================
# get_native_question_domain_nbr_chunks
# =========================================================

def test_get_native_question_domain_pwd():

    native_question, domains, nbr_chunks = (
        get_native_question_domain_nbr_chunks(
            last_intent="x",
            native_question="reset password",
            intent=ActiveIntents.ASK_FORGOT_RESET_PASSWORD.value,
            active_flow=None,
            sscomp_entity_values=[],
            nbr_chunks=2
        )
    )

    assert domains == ["mdp"]
    assert nbr_chunks == 2


def test_get_native_question_domain_resources():

    native_question, domains, nbr_chunks = (
        get_native_question_domain_nbr_chunks(
            last_intent="x",
            native_question="resources",
            intent=ActiveIntents.ASK_ACCESS_RESOURCES_BY_EVALUATOR.value,
            active_flow=None,
            sscomp_entity_values=[],
            nbr_chunks=2
        )
    )

    assert domains == ["resources"]
    assert nbr_chunks == 1


def test_get_native_question_domain_global_advices_with_active_flow():

    native_question, domains, nbr_chunks = (
        get_native_question_domain_nbr_chunks(
            last_intent="x",
            native_question="help",
            intent=ActiveIntents.ASK_GLOBAL_ADVICES_PG.value,
            active_flow="selected_advice_plan",
            sscomp_entity_values=[],
            nbr_chunks=2
        )
    )

    assert domains == ["globaladvices"]
    assert "Proposer conseils" in native_question


def test_get_native_question_domain_procedure():

    native_question, domains, nbr_chunks = (
        get_native_question_domain_nbr_chunks(
            last_intent="x",
            native_question="procedure",
            intent=ActiveIntents.ASK_PROCEDURE_PG.value,
            active_flow=None,
            sscomp_entity_values=[],
            nbr_chunks=2
        )
    )

    assert domains == ["procedure"]


def test_get_native_question_domain_default():

    native_question, domains, nbr_chunks = (
        get_native_question_domain_nbr_chunks(
            last_intent="x",
            native_question="hello",
            intent="UNKNOWN_INTENT",
            active_flow=None,
            sscomp_entity_values=[],
            nbr_chunks=2
        )
    )

    assert domains == []
    assert nbr_chunks == 2

def test_search_expert_all_roles_not_found():
    markdown = """
## Jury
| Role | TI |
|---|---|
| Président de Jury | Ahmed |
"""

    result = search_expert_all_roles("saria", markdown)

    assert result is None

def test_search_expert_all_roles_multiple_results():
    markdown = """
## Jury
| Role | TI |
|---|---|
| Président | Saria |

## Evaluateur
| Role | GL |
|---|---|
| Evaluateur | Saria |
"""

    result = search_expert_all_roles("saria", markdown)

    assert "occupe les fonctions suivantes" in result


def test_get_infos_by_expert_name_entities(monkeypatch):

    tracker = Mock()

    tracker.get_latest_entity_values.return_value = ["expert"]

    result = get_infos_by_expert_name(ActionsLabel.PY_RESPOND_FROM_PDF_FOR_EVAL_PJ, tracker)

    assert isinstance(result, list)

def test_get_infos_by_expert_name_slot_fallback():

    tracker = Mock()

    tracker.get_latest_entity_values.return_value = []

    tracker.get_slot.return_value = ["expert"]

    result = get_infos_by_expert_name(ActionsLabel.PY_RESPOND_FROM_PDF_FOR_EVAL_PJ, tracker)

    assert isinstance(result, list)

def test_get_comp_values_from_synonyms(monkeypatch):

    monkeypatch.setattr(
        "actions.answer_from_file.llm_helpers.get_synonyms_lookup",
        lambda _a, _b: {}
    )

    monkeypatch.setattr(
        "actions.answer_from_file.llm_helpers.get_sscomp_values",
        lambda _q, _s: ["prod_rdi"]
    )

    result = get_comp_values_from_synonyms(
        ActionsLabel.PY_RESPOND_FROM_LANG_CHAIN.value,
        "donner des conseils pour réussir ma prod rdi",
        ["sscomp"]
    )

    assert result == ["prod_rdi"]


def test_load_util_values_none(monkeypatch):
    monkeypatch.setattr(
        "actions.answer_from_file.answer_from_file_actions.get_util_minimal_values_with_log",
        lambda *_a, **_k: None
    )

    from actions.answer_from_file.answer_from_markdown.answer_from_markdown_actions import load_util_values

    with pytest.raises(TypeError):
        load_util_values(FakeTracker(), "label")


def get_latest_entity_values(_key=None):
    return []


class FakeTracker:
    def __init__(self):
        self.slots = {
            "active_flow": "",
            "last_last_question": "",
            "last_answer": "",
            "decision_mode": "short",
            "last_intent": "intent"
        }
        self.latest_action_name = "test_action"

    # ✅ Correction : Utilisation effective du dictionnaire interne pour éviter le warning 'static method'
    def get_slot(self, key):
        return self.slots.get(key, "")

    @property
    def sender_id(self):
        return "user_1"

@pytest.mark.asyncio
# ✅ Correction : Retrait du paramètre 'tracker' inutilisé dans la signature globale de la fonction du test
async def test_evaluators_pj_no_sections(monkeypatch):
    from actions.answer_from_file.answer_from_markdown.answer_from_markdown_actions import ActionEvaluatorsAndPJ

    action = ActionEvaluatorsAndPJ()

    monkeypatch.setattr(
        "actions.answer_from_file.answer_from_markdown.experts_rag.markdown_store.retrieve_sections_with_table_dynamic_bb",
        lambda *_a, **_k: [],
    )

    monkeypatch.setattr(
        "actions.answer_from_file.answer_from_markdown.answer_from_markdown_actions.load_util_values",
        lambda *_a, **_k: ("label", 0, "q", "q2", {}, 1, 1, 0.9, "intent"),
    )

    tracker: Any = FakeTracker()
    dispatcher = Mock()

    result = await action.run(dispatcher, tracker, [])
    assert result is not None

@pytest.mark.asyncio
# ✅ Correction : Retrait du paramètre 'tracker' inutilisé ici aussi
async def test_academic_short_and_detailed(monkeypatch):
    from actions.answer_from_file.answer_from_markdown.answer_from_markdown_actions import ActionAcademicStuff

    tracker: Any = FakeTracker()
    action = ActionAcademicStuff()

    monkeypatch.setattr(
        "actions.answer_from_file.answer_from_markdown.answer_from_markdown_actions.load_util_values",
        lambda *_a, **_k: ("label", 0, "question", "q2", {}, 1, 1, 0.9, "intent"),
    )

    monkeypatch.setattr(
        "actions.answer_from_file.answer_from_markdown.answer_from_markdown_actions.get_decision_mode",
        lambda *_a, **_k: "detailed",
    )

    monkeypatch.setattr(
        "actions.answer_from_file.answer_from_markdown.answer_from_markdown_actions.get_filename_context",
        lambda *_a, **_k: ("file", "ctx", "q"),
    )

    monkeypatch.setattr(
        action,
        "call_llm_safe",
        AsyncMock(return_value="ok"),
    )

    monkeypatch.setattr("actions.utils.message_helpers.send_multiple_messages_forwarded_by_buttons", lambda *_a, **_k: None)
    monkeypatch.setattr("actions.logging.logger.log_chat", AsyncMock())

    result = await action.run(Mock(), tracker, [])
    assert result is not None

# =========================
# FAKE TRACKER
# =========================
class FakeTracker1:
    def __init__(self):
        self.slots = {
            "active_flow": "",
            "last_last_question": "",
            "last_answer": ""
        }

        self.latest_message = {"text": "C'est quoi EFA"}

        self.events = [
            {"event": "user", "text": "C'est quoi EFA"},
            {"event": "bot", "text": "EFA est le grade des débutant au sein des passage de grades"},
            {"event": "user", "text": "et ELCC?"}
        ]

        self.latest_action_name = "langchain_test"

    def get_slot(self, k):
        return self.slots.get(k, "")
