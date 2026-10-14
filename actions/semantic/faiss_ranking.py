"""
actions/semantic/faiss_ranking.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
import secrets
from typing import List, Tuple
from sentence_transformers import util
from actions.constants.Constants import BOT_MESSAGES
from actions.utils.embedding_loader import get_embedder
from actions.utils.models import FAQCandidate

import logging

log = logging.getLogger("rasa-actions")

# ✅ Ranking function : gives you candidates sorted by semantic similarity.
def rank_candidates(user_input: str, candidates: List[FAQCandidate]) -> List[Tuple[FAQCandidate, float]]:
    model = get_embedder()
    query_emb = model.encode(user_input, convert_to_tensor=True)
    cand_embs = model.encode([c.userInput for c in candidates], convert_to_tensor=True)

    scores = util.cos_sim(query_emb, cand_embs)[0].tolist()  # ✅ convert tensor to list

    ranked = sorted(
        zip(candidates, scores),
        key=lambda x: x[1],  # already float
        reverse=True
    )
    return ranked

# ✅ Weighted answer picking : pick the final answer.
def pick_weighted_answer(candidates: list[FAQCandidate]) -> str:
    if not candidates:
        return f"{BOT_MESSAGES.get('no_response')}"

    # Convert Decimal to float for random.choices
    weights = [float(getattr(c, "weight", 1.0)) for c in candidates]

    total_weight = sum(weights)

    if total_weight == 0:
        # Fallback: uniform random if all weights are zero
        return secrets.choice(candidates).botResponse
    else:
        # Secure weighted selection without the 'random' module:
        # 1. Pick a secure random threshold point between 0 and total_weight
        secure_roll = secrets.SystemRandom().uniform(0, total_weight)

        # 2. Find which candidate bounds that point
        current_cumulative = 0.0
        for candidate, weight in zip(candidates, weights):
            current_cumulative += weight
            if secure_roll <= current_cumulative:
                return candidate.botResponse

        # Fallback safety default
        return candidates[-1].botResponse
