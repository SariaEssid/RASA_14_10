from __future__ import annotations  # <-- MUST BE LINE 1

from datetime import datetime
import os
from openai import OpenAI
from aiforge import AIForge

if __name__ == "__main__":
    # Configuration de la clé et de l'adresse de base officielle d'Esprit
    os.environ["AIFORGE_API_KEY"] = "tf-keyyy"

    # Si le constructeur de AIForge accepte un paramètre de base_url ou si l'on configure l'environnement OpenAI :
    os.environ["OPENAI_API_BASE"] = "https://aiforge.esprit.tn/api/v1"

    # Initialisation du client AIForge
    af = AIForge()

    # Optionnel : si le client utilise une instance OpenAI interne, vous pouvez forcer le client de base :
    # af.client.base_url = "https://aiforge.esprit.tn/api/v1"

    print(af.chat("Explique les transformers en deux phrases."))
    print(af.code("Écris un tri rapide en Python"))
    print(af.balance())

    print(datetime.now())