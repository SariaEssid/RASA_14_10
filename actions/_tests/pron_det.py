"""
actions/_tests/pron_det.py

@author ESSID Saria | Copyright (c) 2026. ESPRIT
"""

import spacy

class PRONOUN_LA:
    """
    Classe pour analyser dynamiquement la dépendance des pronoms globaux sur un message utilisateur.
    Version finale résiliente au texte brut en minuscules sans ponctuation ni accents.
    """

    @staticmethod
    def check_pronoun_la(text):
        nlp = spacy.load("fr_core_news_sm")

        doc = nlp(text)
        results = []

        # French subject pronouns that typically precede an object pronoun
        subject_pronouns = {"je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles"}
        pron_det = ["la", "les", "son"]

        nbocc = 0
        for token in doc:
            for pron in pron_det:
                if token.text.lower() == pron:
                    pos = token.pos_
                    dep = token.dep_

                    # --- Robust Structural Checks ---
                    requires_history = False

                    # Check 1: Is it preceded by a subject pronoun? (e.g., "je la...")
                    has_subject_before = False
                    if token.i > 0:
                        prev_token = doc[token.i - 1]
                        if prev_token.text.lower() in subject_pronouns:
                            has_subject_before = True

                    # Check 2: Does it start the sentence followed immediately by a noun?
                    # In "la vie", 'vie' is definitively a noun.

                    if has_subject_before:
                        pos = "PRON"
                        status = "Coreferential Pronoun"
                        requires_history = True
                        explanation = f"Preceded by the subject pronoun '{doc[token.i - 1].text}'. It acts as a direct object pronoun."

                    # Fallback to spaCy if no clear pronoun rule hits
                    elif pos == "DET":
                        status = "Local Definition (Determiner)"
                        requires_history = False
                        explanation = f"Defines the noun '{token.head.text}' within the same context."
                    elif pos == "PRON":
                        status = "Coreferential Pronoun"
                        requires_history = True
                        explanation = "Acts as a direct object pronoun."
                    else:
                        status = "Other"
                        requires_history = False
                        explanation = f"Analyzed as {pos}/{dep}."

                    results.append({
                        "token": token.text,
                        "pos_tag": pos,
                        "status": status,
                        "requires_history": requires_history,
                        "explanation": explanation
                    })

                    if pos == "PRON":
                        nbocc += 1

        return nbocc


# --- Zone de Test ---
if __name__ == "__main__":
    qe_1 = "je la deteste"
    qe_2 = "préciser son parcours academique"
    qe_3 = "donner son lieu de deroulement"
    qe_4 = "est ce que le type de cette epreuve est pdf ou video"
    qe_5 = "j'ai essaye de charger ma capsule sur la plateforme pgpg, mais ca marche pas"

    print("QE-1 : " + str(PRONOUN_LA.check_pronoun_la(qe_1)))
    print("QE-2 : " + str(PRONOUN_LA.check_pronoun_la(qe_2)))
    print("QE-3 : " + str(PRONOUN_LA.check_pronoun_la(qe_3)))
    print("QE-4 : " + str(PRONOUN_LA.check_pronoun_la(qe_4)))
    print("QE-5 : " + str(PRONOUN_LA.check_pronoun_la(qe_5)))