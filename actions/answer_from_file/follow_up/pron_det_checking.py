"""
actions/answer_from_file/follow_up/detect_rooting.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
import re

import spacy
import unicodedata

try:
    nlp = spacy.load("fr_core_news_sm")
except OSError:
    raise ImportError("Veuillez installer le modèle français : python -m spacy download fr_core_news_sm")

# 1. Déterminants & démonstratifs dépendant de l'historique
POSSESSIVES = {
    "son",
    "sa",
    "ses",
    "leur",
    "leurs"
}

DEMONSTRATIVES = {
    "ce",
    "cet",
    "cette",
    "ces"
}

STRICT_DEPENDENT_WORDS = POSSESSIVES | DEMONSTRATIVES
# 2. Pronoms personnels, démonstratifs neutres et indéfinis
PRON_TARGETS = {"il", "elle", "ils", "elles", "ca", "ça", "cela", "chacun", "chacune"}

# 3. Pronoms objets clitiques & sujets/négations
CLITIC_PRONOUNS = {"le", "la", "les"}
SUBJECT_OR_NEGATION = {"je", "j'", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles", "ne", "n'"}

# Expressions impersonnelles à ignorer
IMPERSONAL_PATTERNS = {"s'agit il", "s'agit-il", "il s'agit", "s agit il"}


def check_pronoun_det(text: str) -> bool:
    normalized_text = normalize_text(text)
    doc = nlp(normalized_text)
    words = [t.text for t in doc]
    score = 0

    # --------------------------------------------------
    # 1. POSSESSIFS & DÉMONSTRATIFS (Anaphores strictes)
    # --------------------------------------------------
    text_without_est_ce_que = (
        normalized_text.replace("est ce que", "")
        .replace("est-ce que", "")
        .replace("qu'est ce que", "")
        .replace("qu'est-ce que", "")
    )
    words_clean_for_strict = text_without_est_ce_que.split()

    has_strict_dep = any(w in STRICT_DEPENDENT_WORDS for w in words_clean_for_strict)
    if has_strict_dep:
        score += 2

    # --------------------------------------------------
    # 0. PATTERNS DE QUESTIONS FACTUELLES (Sans anaphore)
    # --------------------------------------------------
    fact_question_patterns = ["est ce que", "est-ce que", "qu'est ce que", "qu'est-ce que"]
    # IMPORTANT : Ne PAS déduire de points si la phrase contient un déterminant démonstratif/possessif strict !
    if any(p in normalized_text for p in fact_question_patterns) and not has_strict_dep:
        score -= 2

    # --------------------------------------------------
    # 2. PRONOMS SUJETS / NEUTRES / INDÉFINIS
    # --------------------------------------------------
    is_impersonal = any(p in normalized_text for p in IMPERSONAL_PATTERNS)

    # Détecter si un sujet explicite (Nom propre ou Nom commun) précède le pronom dans la même phrase
    has_earlier_subject = False
    refer_pronoun = False
    seen_subject = False
    for token in doc:
        if token.dep_ in {"nsubj", "nsubj:pass"} or token.pos_ in {"PROPN", "NOUN"}:
            seen_subject = True

        if token.dep_.startswith("expl"):
            refer_pronoun = True
            continue

        if token.text in PRON_TARGETS and seen_subject:
            # Si le sujet vu avant n'est pas lui-même un pronom de la liste PRON_TARGETS
            if token.i > 0 and doc[token.i - 1].pos_ in {"PROPN", "NOUN", "VERB", "AUX"}:
                has_earlier_subject = True

    has_pron_target = any(w in PRON_TARGETS for w in words)

    if has_pron_target and not is_impersonal and not has_earlier_subject and not refer_pronoun:
        score += 2

    # --------------------------------------------------
    # 3. PRONOMS OBJETS CLITIQUES (le, la, les)
    # --------------------------------------------------
    for i, t in enumerate(doc):
        if t.text in CLITIC_PRONOUNS:
            prev_token = doc[i - 1] if i > 0 else None
            next_token = doc[i + 1] if i + 1 < len(doc) else None

            # Sujet/Négation + Clitique (ex: 'je la...', 'tu le...', 'il les...')
            if prev_token and prev_token.text in SUBJECT_OR_NEGATION:
                return True

            # Si le mot suivant est un nom/adj/propn (déterminant article, ex: "les candidats")
            if next_token and next_token.pos_ in {"NOUN", "PROPN", "ADJ"}:
                continue

            if t.pos_ == "PRON":
                return True

            if prev_token and (prev_token.pos_ in {"VERB", "AUX"} or i == len(doc) - 1 or (
                    next_token and next_token.text in {"en", "de", "dans"})):
                return True

    # --------------------------------------------------
    # 4. CORRÉFÉRENCE INTERNE DYNAMIQUE (SELF-CONTAINMENT)
    # --------------------------------------------------
    clauses = re.split(r'[,;.]|\b(?:mais|donc|car|cependant|alors)\b', normalized_text)
    is_multi_clause = len(clauses) > 1

    first_clause_text = clauses[0].strip()
    first_clause_doc = nlp(first_clause_text)
    first_clause_words = [t.text for t in first_clause_doc]

    strict_in_first = [w for w in first_clause_words if w in STRICT_DEPENDENT_WORDS]
    has_strict_dep_in_first_clause = len(strict_in_first) > 0

    has_internal_antecedent = has_local_antecedent(first_clause_doc)

    content_words_first_clause = [
        t for t in first_clause_doc
        if not t.is_punct and t.text not in SUBJECT_OR_NEGATION and t.text not in STRICT_DEPENDENT_WORDS
    ]

    has_local_context = (
            any(t.pos_ in {"PROPN", "NOUN", "VERB"} or t.ent_type_ for t in first_clause_doc)
            and len(content_words_first_clause) >= 3
    )

    can_neutralize = (not has_strict_dep_in_first_clause) or has_internal_antecedent

    if is_multi_clause and has_local_context and can_neutralize:
        score -= 2
    elif has_internal_antecedent and len(doc) > 6:
        score -= 2

    # --------------------------------------------------
    # 5. MANQUE DE SUBSTANCE NOMINALE
    # --------------------------------------------------
    has_named_entity = any(t.ent_type_ or t.pos_ == "PROPN" for t in doc)
    has_nouns = sum(1 for t in doc if t.pos_ == "NOUN")

    if not has_named_entity and has_nouns == 0 and not is_impersonal:
        meaningful_words = [t for t in doc if not t.is_punct]
        if len(meaningful_words) <= 5:
            score += 1

    return score >= 2

def has_local_antecedent(doc) -> bool:
    for token in doc:

        if token.text not in STRICT_DEPENDENT_WORDS:
            continue

        head = token.head

        if head.pos_ != "NOUN":
            continue

        # -----------------------------
        # POSSESSIVES
        # -----------------------------
        if token.text in POSSESSIVES:

            # Any noun before the possessive is enough
            for previous in doc[:token.i]:
                if previous.pos_ in {"NOUN", "PROPN"}:
                    return True

        # -----------------------------
        # DEMONSTRATIVES
        # -----------------------------
        else:

            # Require the SAME noun to have appeared before
            for previous in doc[:head.i]:
                if (
                        previous.pos_ in {"NOUN", "PROPN"}
                        and previous.lemma_ == head.lemma_
                ):
                    return True

    return False

def normalize_text(textq: str) -> str:
    sss = textq.lower().replace("’", "'")
    sss = sss.replace("chaqu'un", "chacun").replace("chaqu'une", "chacune")
    return "".join(
        c for c in unicodedata.normalize('NFD', sss)
        if unicodedata.category(c) != 'Mn'
    )
