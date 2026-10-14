from __future__ import annotations  # <-- MUST BE LINE 1

from datetime import datetime
from typing import Union

from openai import OpenAI
from aiforge import AIForge

class DeepSeekClient:
    """
    Wrapper using OpenRouter (FREE tier samples like DeepSeek).
    """

    # Option A: Using Union
    def __init__(self, api_key: Union[str, None] = None):


        # OpenRouter key (NOT DeepSeek key anymore)
        self.api_key = "tf-C5yi8ytBiSob_jtonQDyKssUkeYD5RtBq_rKhSLhAMZ9B9ls"
        if not self.api_key:
            raise ValueError("OpenRouter API key is missing.")

        # OpenRouter OpenAI-compatible endpoint
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://aiforge.esprit.tn/api/v1"
        )

    def ask(
            self,
            system_mission: str,
            prompt: str,
            model: str = "Qwen3.6-35B-A3B",
            temperature: float = 0.1
    ) -> str:
        """
        Send prompt to OpenRouter DeepSeek model and return response.
        """

        try:

            #af = AIForge()  # clé depuis AIFORGE_API_KEY
            #print(af.chat("Explique les transformers en deux phrases."))
            #print(af.code("Écris un tri rapide en Python"))
            #print(af.balance())

            response = self.client.chat.completions.create(
                model=model,
                messages=[] or get_messages(system_mission, prompt),
                temperature=temperature,
                stream=False
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"OpenRouter API Error: {str(e)}"


# ==========================================================
# Main
# ==========================================================
agent_mission = """
<|system|>
Tu es un ROBOT assistant expert, rigoureux et sympa chargé d'assiter les candidats Enseignants durant leurs Passages de grades (Enseignant Formateur (EF), Enseignant de Langue Communication et Citoyenneté (ELCC)) via le système de passage de grade ```PGPG```.       
- Ne jamais confondre : y a pas de ÉLÈVE -> CANDIDAT = ENSEIGNANT
"""

user_qe_context = """
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

    Question précédente : comment **pour Robot ChatBot.**
    Question actuelle : 👍 D'accord, 👉 J'ai besoin tout d'abord de me préciser votre Nom Utilisateur et votre Mot de Passe sous format username=VotreIdentifiant ; password=VotreMotDePassePGPG.

    Règles de formatage :
    - Retourne uniquement la question fusionnée finale.
    - Pas d'explication, pas de guillemets, une seule ligne.

    <|end|>
    <|assistant|>
"""

def get_messages(system_message, prompt):
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]
    return messages

if __name__ == "__main__":
    client = OpenAI(
        base_url="https://aiforge.esprit.tn/api/v1",
        api_key="tf-C5yi8ytBiSob_jtonQDyKssUkeYD5RtBq_rKhSLhAMZ9B9ls",
    )

    response = client.chat.completions.create(
        model="Qwen3.6-35B-A3B",
        messages=get_messages(agent_mission, user_qe_context) or [],
        temperature=0.1,
        stream=False
    )


    print(response.choices[0].message.content)
    # Windows PowerShell:
    # $env:OPENROUTER_API_KEY="your_key"

    # Linux/Mac:
    # export OPENROUTER_API_KEY="your_key"

    ai = DeepSeekClient()

    print(f"{datetime.now()} : Connecting to OpenRouter (DeepSeek)...\n\n")

    result = ai.ask(agent_mission, user_qe_context)

    print("---- RESPONSE ----")
    print(result)
    print("------------------\n\n")

    print(datetime.now())

