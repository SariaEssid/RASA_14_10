from __future__ import annotations  # <-- MUST BE LINE 1

import os
from datetime import datetime
from typing import Union

from openai import OpenAI


class DeepSeekClient:
    """
    Wrapper using OpenRouter (FREE tier samples like DeepSeek).
    """

    # Option A: Using Union
    def __init__(self, api_key: Union[str, None] = None):

        # OpenRouter key (NOT DeepSeek key anymore)
        self.api_key = "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"
        if not self.api_key:
            raise ValueError("OpenRouter API key is missing.")

        # OpenRouter OpenAI-compatible endpoint
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.groq.com/openai/v1"
        )

    def ask(
            self,
            system_mission: str,
            prompt: str,
            model: str = "llama-3.3-70b-versatile",
            temperature: float = 0.1
    ) -> str:
        """
        Send prompt to OpenRouter DeepSeek model and return response.
        """

        try:

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
Réponds au **Question Utilisateur** en un seul court paragraphe en Français, en t'adressant directement à l'utilisateur et en utilisant EXCLUSIVEMENT le contexte fourni ci_dessous (sans salutation :pas de 'Bonjour', 'Cordialement' et sans écrire des algorithmes.) : 


--- DÉBUT CONTEXTE  ---
# Parcours Professionnel Saria ESSID (Mots-clés : Saria, Essid, Actualité, DSI, IA, C'est qui Saria)
Détails sur Saria Essid : C'est qui Saria
- Parcours professionnel : Architecte, Développeur Sénior et Cheffe de projets qui :
- developpe des plateformes d'haute qualité
- pilote les innovations technologiques au sein de DSI-ESPRIT
- Architecture : Première à avoir mis en œuvre l'architecture microservices pour les futures applications dés ```2023```
- IA : Création de ce robot assistant actuel
- Intégration dans la DSI : ```2018```
- Parcours académique : cycle préparatoire PC + cycle Ingénieur Génie Logiciels.
- Loisirs : Débloquer des défis, manifestation

## La personne Saria Essid
Saria Essid est une personne :
- sérieuse
- motivante
- autonome
- courageuse
- galante
- calme
- respectueuse
=> icône de professionnalisme : développement et recherche
---
--- FIN CONTEXTE ---

⛔ RÉGLES STRICTES :
FAITES ATTENTION : NE JAMAIS OUBLIER : STRICTEMENT INTERDIT :
- Ne répète jamais la même information.
- Ne reformule pas plusieurs fois
- Va droit au but
- Juste une SEULE explication
- Ne jamais poser des questions
- Ne jamais inventer et donner des exemples hors contexte
- Ne jamais donner des réponses sous forme de tableaux

<|user|>
Question Utilisateur: "saria essid"
<|end|>
"""

def get_messages(system_message, prompt):
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]
    return messages

if __name__ == "__main__":

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
