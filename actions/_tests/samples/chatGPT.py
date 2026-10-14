from __future__ import annotations  # <-- MUST BE LINE 1

import os
from datetime import datetime
from typing import Union

from openai import OpenAI


class ChatGPTClient:
    """
    Wrapper for the official OpenAI ChatGPT API.
    """

    def __init__(self, api_key: Union[str, None] = None):

        self.api_key = "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"

        if not self.api_key:
            raise ValueError("OpenAI API key is missing.")

        self.client = OpenAI(
            api_key=self.api_key
        )

    def ask(
        self,
        system_mission: str,
        prompt: str,
        model: str = "gpt-5-mini",
        temperature: float = 0.1,
    ) -> str:
        """
        Send prompt to ChatGPT and return the response.
        """

        try:

            response = self.client.chat.completions.create(
                model=model,
                messages=get_messages(system_mission, prompt),
                temperature=temperature,
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"OpenAI API Error: {str(e)}"


# ==========================================================
# Prompt builder
# ==========================================================

def get_messages(system_message, prompt):
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": prompt},
    ]


# ==========================================================
# Main
# ==========================================================

agent_mission = """
Tu es un ROBOT assistant expert, rigoureux et sympa chargé d'assister les candidats Enseignants durant leurs Passages de grades (Enseignant Formateur (EF), Enseignant de Langue Communication et Citoyenneté (ELCC)) via le système PGPG.

- Ne jamais confondre :
  Il n'y a pas d'ÉLÈVE.
  Le candidat est un ENSEIGNANT.
"""

user_qe_context = """
Réponds au Question Utilisateur en un seul court paragraphe en Français,
en utilisant EXCLUSIVEMENT le contexte fourni.

Question Utilisateur :
saria essid
"""


if __name__ == "__main__":

    # Windows PowerShell
    # $env:OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxx"

    # Linux / macOS
    # export OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxx"

    ai = ChatGPTClient()

    print(f"{datetime.now()} : Connecting to OpenAI...\n")

    result = ai.ask(agent_mission, user_qe_context)

    print("---- RESPONSE ----")
    print(result)
    print("------------------")

    print(datetime.now())