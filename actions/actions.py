"""
actions/actions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
import asyncio
import logging
import os
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

import unicodedata
from sklearn.metrics.pairwise import cosine_similarity

from actions.constants.Constants import BOT_MESSAGES, ALL_COMPOSANTES_PRINCIPALES
from actions.logging.logging_helpers import log_info_text, log_warn_text
from actions.semantic.faiss_ranking import rank_candidates, pick_weighted_answer
from actions.settings.settings import settings
from actions.utils.embedding_loader import get_embedder
from actions.utils.message_helpers import get_random_message
from actions.utils.models import FAQCandidate

log = logging.getLogger("rasa-actions")
START_WORDS = ("mais", "et", "et pour", "et puis", "et concernant", "non", "oui", "donc", "meme", "même", "alors", "pas", "aucun")

EXCLUDED_PATTERNS = [
    "est-ce qu",
    "est ce qu",
    "sont-ils",
    "sont ils",
    "sont-elles",
    "sont elles",
    "est il",
    "t-il",
    "t il",
    "est elle",
    "t-elle",
    "t elle",
    "qu'il y"
]

def remove_excluded_patterns(sentence: str) -> str:
    s = sentence.lower()
    for pattern in EXCLUDED_PATTERNS:
        s = s.replace(pattern, "")
    return s.strip()

def check_is_excluded(sentence: str) -> bool:
    s = sentence.lower()
    return any(pattern in s for pattern in EXCLUDED_PATTERNS)

def get_payload(user_id, session_id, user_input, rasa_intent, confidence):
    return {
        "userId": user_id,
        "sessionId": session_id,
        "userInput": user_input,
        "rasaIntent": rasa_intent,
        "confidence": confidence,
        "messageExchangeDate": datetime.now(timezone.utc).isoformat()
    }

def get_semantic_random_reply(candidates_data, action_label, user_input, top_k: int = 3):

    # Convert to dataclass for type safety
    candidates: List[FAQCandidate] = [
        FAQCandidate(
            id_faq=c.get("id_faq"),
            userInput=c.get("userInput", ""),
            botResponse=c.get("botResponse", ""),
            weight=Decimal(str(c.get("weight", 1.0))),
        )
        for c in candidates_data if isinstance(c, dict)
    ]

    # ---- No candidates ----
    if not candidates:
        reply = BOT_MESSAGES.get("no_response")
        log_info_text(action_label, f"No candidates found for {user_input} : {reply}")
        return reply

    # ---- Semantic ranking ----
    ranked_candidates = rank_candidates(user_input, candidates)

    if not ranked_candidates:
        log_warn_text(action_label, "Ranking failed, using random fallback.")
        reply = secrets.choice(candidates).botResponse
        return (reply or "").replace(" \\n", "\n")

    # ------------------------------------------------
    # ✅ NEW LOGIC: select from Top-K semantic matches
    # ------------------------------------------------

    # Take top-k ranked results
    top_ranked = ranked_candidates[:top_k]

    # Extract FAQ objects
    top_faqs = [faq for faq, _score in top_ranked]

    # Collect candidates from same semantic group
    semantic_pool = [
        c for c in candidates
        if any(c.userInput == faq.userInput for faq in top_faqs)
    ]

    if semantic_pool:
        reply = pick_weighted_answer(semantic_pool)
    else:
        reply = secrets.choice(top_faqs).botResponse

    # ---- Clean reply ----
    return (reply or "").replace(" \\n", "\n")

def generate_composante_buttons() -> list[dict]:
    buttons = [
        {
            "title": name,
            "payload": f'/select_comp_for_guide{{"sscomp":"{name}"}}'
        }
        for name in ALL_COMPOSANTES_PRINCIPALES
    ]

    # 👇 add your custom button after the loop
    buttons.append({
        "title": "🔙 Retourner au Mini-Guide",
        "payload": "/stressed_candidat"
    })

    return buttons

def append_friendly_intro_to_answer(answer):
    formed_intro_msg = get_random_message(BOT_MESSAGES['friendly_intro']) + "\n\n"
    formed_intro_msg += clean_llm_response(answer)

    log_info_text("FIRST : ", formed_intro_msg)
    log_info_text("FINAL : ", bypass_words(formed_intro_msg.strip()) + ".")

    return bypass_words(formed_intro_msg.strip())

def bypass_words(text: str) -> str:
    words_to_bypass = [
        "<|system|>",
        "---",
        "---"
    ]

    pattern = '|'.join(map(re.escape, words_to_bypass))

    res = re.sub(pattern, '', text, flags=re.IGNORECASE)

    # Remove empty lines
    res = re.sub(r'\n\s*\n', '\n', res)

    # Normalize spaces
    res = re.sub(r'[ \t]+', ' ', res)

    return res.strip()

def clean_response(text):
    last_dot = text.rfind(".")
    if last_dot != -1:
        return text[: last_dot + 1]
    return text

def format_response_steps(text: str) -> str:
    if not text:
        return ""

    text = text.strip()

    # Normalize line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Fix numbered lists
    text = re.sub(r'(\d+\.)\s*\n+\s*', r'\1 ', text)

    # Repair if text is cut off
    if not text.endswith('.'):
        text = clean_response(text)

    return text

def clean_llm_response(text):
    # 1. Supprime les lignes qui ne contiennent que des espaces
    text = re.sub(r'^\s*$', '', text, flags=re.MULTILINE)

    # 2. Remplace 3 sauts de ligne ou plus par un seul (ou deux max)
    text = re.sub(r'\n\s*\n+', '\n', text)

    return reformulate_session_if_hallucinate(text).strip()

def get_extracted_slots(action_label, tracker):
    slot_grade_value = tracker.get_slot("grade") or None
    slot_speciality_value = tracker.get_slot("speciality") or None
    slot_session_value = tracker.get_slot("session") or None
    slot_sscomp_value = tracker.get_slot("sscomp") or None
    slot_expert_value = tracker.get_slot("expert") or None

    log_info_text(action_label, f"🚀 🚀 🚀  SLOT Entities GRADE : {slot_grade_value}")
    log_info_text(action_label, f"🚀 🚀 🚀  SLOT Entities SPECIALITY : {slot_speciality_value}")
    log_info_text(action_label, f"🚀 🚀 🚀  SLOT Entities SESSION : {slot_session_value}")
    log_info_text(action_label, f"🚀 🚀 🚀  SLOT Entities SSCOMP : {slot_sscomp_value}")
    log_info_text(action_label, f"🚀 🚀 🚀  SLOT Entities EXPERT : {slot_expert_value}")

    return slot_speciality_value, slot_grade_value, slot_session_value, slot_sscomp_value, slot_expert_value # , user_question

##########################################################################
PDF_WARMUP_QUERIES = {
    # normalize_path(settings.PATH_HIERARCY): "donner le nom de Composante 1",
    # normalize_path(settings.PATH_HIERARCY_DATE): "donner date test qcm",
    # normalize_path(settings.PATH_HIERARCY_DURATION): "donner durée test qcm",
    # normalize_path(settings.PATH_HIERARCY_EXAM_KIND): "est ce que production rdi est pdf",
    # normalize_path(settings.PATH_HIERARCY_PLACE): "est ce que test qcm se fait en présentiel",
    # normalize_path(settings.PATH_HIERARCY_SCORE): "donner score test qcm",
    # normalize_path(settings.PATH_PG_ADVICES): "conseils pour test qcm",
    # normalize_path(settings.PATH_PG_SUFFISIANT_EXCEPTIONAL): "qui met ma candidature exceptionnelle",
}

PDF_WARMED = set()
SEM = None
WARM_LOCK = None

# --- 2. Tool Provider (Prevents "Different Loop" Error) ---
def get_async_tools():
    global SEM, WARM_LOCK
    if SEM is None:
        SEM = asyncio.Semaphore(3)
    if WARM_LOCK is None:
        WARM_LOCK = asyncio.Lock()
    return SEM, WARM_LOCK


def reformulate_session_if_hallucinate(answer):
    hallucunate_session = "-2"
    if hallucunate_session in answer:
        answer = ajuster_session_passage_grade(answer)
    # log_info_text("PIKATCHU: ", answer)
    return answer

def ajuster_session_passage_grade(text):
    # 3. Correction dynamique de l'année (2024-2... ou 2025-2...)
    # Le pattern cherche 4 chiffres (\d{4}) suivis de "-2" et de lettres
    def replacement_logic(match):
        year_start = int(match.group(1))
        year_end = year_start + 1
        return f"{year_start}-{year_end}"

    pattern = r"(\d{4})-2[a-z]+"
    return re.sub(pattern, replacement_logic, text, flags=re.IGNORECASE)

def normalize_text(text: str) -> str:
    # Passe en minuscule, remplace les apostrophes courbes et retire les accents
    text = text.lower().replace("’", "'")
    text = text.replace("chaqu'un", "chacun").replace("chaqu'une", "chacune")
    text = text.replace("chaq'un", "chacun").replace("chaq'une", "chacune")
    return "".join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


def get_local_header(elapsed: float, file_kind: str,  path_pdf: str):
    return f"*```({elapsed} sec | {file_kind} | {get_name(path_pdf)})```* \n"

def get_name(file_path):
    file_name_full = os.path.basename(file_path)  # Résultat: hierarchy_score.pdf

    # Définir le préfixe à supprimer
    prefix_to_remove = "hierarchy_"

    # Vérifier si le préfixe est là et le supprimer
    if file_name_full.startswith(prefix_to_remove):
        final_name = file_name_full.replace(prefix_to_remove, "", 1)
    else:
        final_name = file_name_full

    return final_name

def get__decision_mode__last_intent(action_label, tracker):
    decision_mode = tracker.get_slot("forward_level")
    last_intent = tracker.get_slot("last_intent") or ""

    if last_intent:
        log_info_text(action_label, "🔁 🔁 🔁 🔁 🔁  CATCHA-0 last_intent : " + last_intent)

    if decision_mode:
        log_info_text(action_label, "🔁 🔁 🔁 🔁 🔁  CATCHA-1 decision_mode : " + decision_mode)

    return decision_mode, last_intent

def normalize_text_strict(text):
    """
    Normalise le texte : passage en minuscules, suppression des accents,
    nettoyage de la ponctuation et des espaces superflus.
    """
    # 1. Passage en minuscules
    text = text.lower()

    # 2. Suppression des accents (décomposition Unicode)
    # Exemple: 'é' devient 'e' + '´', puis on garde uniquement le 'e'
    text = unicodedata.normalize('NFD', text)
    text = "".join([c for c in text if unicodedata.category(c) != 'Mn'])

    # 3. Remplacer la ponctuation par des espaces
    text = re.sub(r'[^\w\s]', ' ', text)

    # 4. Supprimer les espaces multiples et les espaces en début/fin
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def is_followup(current_question, last_question):

    if not last_question:
        return False

    words = current_question.split()

    # Rule 1 — short questions are likely follow-ups
    if len(words) <= 3:
        return True

    embed_model = get_embedder()
    emb_current = embed_model.encode([current_question])
    emb_last = embed_model.encode([last_question])

    similarity = cosine_similarity(emb_current, emb_last)[0][0]

    log_info_text("OLD : ", last_question)
    log_info_text("NEW :", current_question)
    log_info_text("👉   👉   👉   👉   👉   Follow-up similarity : ", str(similarity) + " - " + str(len(words)))

    return similarity > settings.FOLLOWUP_THRESHOLD