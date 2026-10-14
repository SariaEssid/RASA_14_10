import requests
import json


class GeminiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # CORRECTION : Utilisation de la version v1 (recommandée) ou v1beta avec le nom exact du modèle
        self.url = f"https://googleapis.com{self.api_key}"

    def ask(self, system_mission: str, prompt: str) -> str:
        # Configuration propre du payload en utilisant system_instruction
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "system_instruction": {
                "parts": [{"text": system_mission}]
            }
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(self.url, headers=headers, json=payload)
            data = response.json()

            if "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return f"Erreur API: {data}"

        except Exception as e:
            return f"Erreur de connexion: {str(e)}"


if __name__ == "__main__":
    # ATTENTION : Pensez à sécuriser votre clé API (ne pas la laisser en clair en production)
    my_api_key = "aq.ab8rn6j7v09fdk0o8dpuuflbhnx_mfekv9q1e9zcqlawa_dngg"

    ai = GeminiClient(my_api_key)
    result = ai.ask("Tu es un assistant expert.", "Qui est Saria Essid ?")

    print("---- Response ----")
    print(result)
