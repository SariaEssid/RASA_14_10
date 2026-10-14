import logging

log = logging.getLogger(__name__)

class HILA:
    """
    Classe pour nettoyer et formater les réponses textuelles.
    """

    @staticmethod
    def detecter_mots_cles(phr, liste_cibles):
        # On convertit la phrase en minuscules pour une détection plus robuste
        phrase_clean = phr.lower()

        # Vérifie si n'importe quel mot de la liste est dans la phrase
        return any(cible.lower() in phrase_clean for cible in liste_cibles)


# --- Zone de Test ---
if __name__ == "__main__":
    mots_a_detecter = ["sa", "son", "ses", "leur", "leurs", "cet", "cette", "ce", "elle", "il", "elles", "ils", "ce dernier", "ces derniers", "detail", "expliq", "pourquoi"]

    # Test
    phrase = "détailler la vie en rose  ."
    log.info(f"NEW : {phrase}")

    resultat = HILA.detecter_mots_cles(phrase, mots_a_detecter)

    print(f"Correspondance trouvée : {resultat}")