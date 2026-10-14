"""
actions/_tests/fusion_questions.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

class FusionQuestions:
    """
    Classe pour nettoyer et formater les réponses textuelles.
    """

    @staticmethod
    def fusion_questions(last_question, current_question):
        return f"""
<|user|>
Tu es un assistant expert en traitement du langage et en résolution de coréférences.
Ton rôle est de fusionner la "Question actuelle" et la "Question précédente" pour générer une unique question utilisateur autonome, claire et très courte.

Voici des exemples de comportements attendus :

---
Exemple 1 : Changement/Substitution de sujet ("et pour...")
Question précédente : donner des conseils pour reussir ma prod rdi
Question actuelle : et pour ptp
Question fusionnée : donner des conseils pour reussir ma ptp

Exemple 2 : Résolution de pronom ciblant le sujet principal
Question précédente : est ce que dissertations fait partie de Dossier & Entretien
Question actuelle : donner son lieu de deroulement
Question fusionnée : donner le lieu de deroulement des dissertations

Question précédente : preciser la date de deroulement de diss fr
Question actuelle : est ce que cette epreuve est de type pdf ou video
Question fusionnée : est ce que diss fr est de type pdf ou video

Exemple 3 : Complétion contextuelle simple
Question précédente : Quels sont les documents requis pour l'inscription ?
Question actuelle : et la date limite ?
Question fusionnée : Quelle est la date limite pour l'inscription ?

---

Applique la même logique stricte pour les données suivantes :

Question précédente : donner le lieu de déroulement de la séquence d’enseignement
Question actuelle : tu es méchant

Règles de formatage :
- Retourne uniquement la question fusionnée finale.
- Pas d'explication, pas de guillemets, une seule ligne.

<|end|>
<|assistant|>"""

# --- Zone de Test ---
if __name__ == "__main__":
    last_question = "comment **pour Robot ChatBot.**"
    current_question = "👍 D'accord, 👉 J'ai besoin tout d'abord de me préciser votre Nom Utilisateur et votre Mot de Passe sous format username=VotreIdentifiant ; password=VotreMotDePassePGPG."
    result = FusionQuestions.fusion_questions(last_question, current_question)

    print(result)