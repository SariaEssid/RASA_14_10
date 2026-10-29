"""
actions/constants/Constants.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.constants.ActiveIntents import ActiveIntents
from actions.settings.settings import settings

ALL_COMPOSANTES_PRINCIPALES = ["Composante 1", "Composante 2", "Composante 3"]

ALL_SLOTS = [
    "active_flow",
    "id_candidat",
    "full_name",
    "roles",
    "last_question",
    "last_answer",
    "predicted_intent",
    "sscomp",
    "session",
    "language",
    "speciality",
    "expert",
    "grade",
    "forward_level",
    "last_intent",
    "last_last_question",
    "last_action"
]

FEEDBACK_BUTTONS = [
    {"title": "👍 utile", "payload": "/affirm_helpful"},
    {"title": "👎 inutile", "payload": "/deny_helpful"}
]

ADVICE_PLANNING_BUTTONS = [
    {"title": "Présenter Planning", "payload": "/ask_about_candidature_passage_grade"},
    {"title": "Proposer Conseils", "payload": "/ask_global_advices_pg"},
    {"title": "Booster ma motivation", "payload": "/affirm_advice_1"}
]

GRILLE_SS_COMPOSANTES = [
    {"title": "Test QCM", "payload": '/select_comp_for_guide{"sscomp":"Test QCM"}'},
    {"title": "Dissertations", "payload": '/select_comp_for_guide{"sscomp":"Dissertations"}'},
    {"title": "Capsules", "payload": '/select_comp_for_guide{"sscomp":"Capsules Pédagogiques"}'},
    {"title": "Séquence Ens.", "payload": '/select_comp_for_guide{"sscomp":"Séquence Enseignement"}'},
    {"title": "Plateforme de TP", "payload": '/select_comp_for_guide{"sscomp":"Plateforme de TP"}'},
    {"title": "Supports Pédagogiques", "payload": '/select_comp_for_guide{"sscomp":"Supports Pédagogiques"}'},
    {"title": "Production RDI", "payload": '/select_comp_for_guide{"sscomp":"Production RDI"}'},
    {"title": "Dossier", "payload": '/select_comp_for_guide{"sscomp":"Dossier"}'},
    {"title": "Entretien avec Jury", "payload": '/select_comp_for_guide{"sscomp":"Entretien avec les jurys"}'}
]

BOT_MESSAGES = {
    "failed_auth": "🔐 Échec d'authentification.\n⚠️ Nom utilisateur et/ou Mot de passe incorrect(s).",
    "success_auth": "✅ Authentification réussie.\n👤 Vous êtes ",
    "friendly_intro": [
            "🚀 Super !,",
            "🙌 Question Intéressante!,",
            "😎 Très pertinent comme question !,",
            "✍️ C'est noté,",
            "👏 Excellente question !,",
            "🌸 Bien sûr,",
            "👌 Compris !,",
            "🙌 Parfait !,",
            "🙌 Tout à fait,",
            "🎯 J'apprécie votre question !,",
            "🌟 Parfait,",
            "🧠 C'est génial !,",
            "💖 Magnifique,",
            "👍 Bonne remarque,",
            "✅ D’accord !,",
            "🌺 Merci pour votre question !,",
            "👍 Trés précieuse comme remarque,",
            "😍 Avec plaisir,",
            "🧠 Bonne question !,",
            "🎯 Excellent,",
            "😊 Certainement,",
            "🤗 Bien entendu,"
    ],
    "too_log_message":[
        "Oopsy 😅 Ton message est un peu trop long !\n Essaie de rester sous les 200 mots pour que je puisse bien te comprendre 🚀",
        "Whoa 😅 Trop de mots d’un coup !  \nGarde ton message sous 200 mots pour que je capte tout correctement 🧐",
        "Oopsy 😬 Ton message est un peu chargé !  \nDécoupe-le en moins de 200 mots pour que je puisse te répondre au mieux 📝",
        "😅 Eh, ça fait un sacré pavé !  \nEssaie de rester sous 200 mots pour que je comprenne tout correctement 🚀",
        "😅 Trop de mots là !  \nRéduis à 200 mots max pour que je capte tout parfaitement 👍",
        "Whoa 😮 Ton message est un peu long !  \nGarde-le sous 200 mots pour que je puisse te suivre facilement 🧐",
        "😅 Ça fait beaucoup d’infos en une fois !  \nEssaie de rester sous 200 mots pour que je te comprenne mieux ✨"
    ],
    "fallback_dsi": [
        "Oopsy ! 💥 Un problème technique est survenu.\nNotre équipe est déjà notifiée 🛠️ et travaille à la résolution.\nVeuillez réessayer ultérieurement. Merci de votre patience ! 🙏",
        "Oopsy ! 😬 On dirait qu'il y a un petit pépin technique.\nPas d'inquiétude, nos experts sont sur le coup 🧑‍💻 pour régler ça !\nRevenez nous voir dans quelques minutes. Merci ! 😊",
        "🙏 Mes excuses, Problème technique temporaire.\n📨 Nous avons été informés et travaillons dessus.\nMerci de réessayer plus tard. ⏳",
        "Désolé 😔 , une erreur inattendue est survenue. 🛑\n📨 L'alerte a été envoyée à notre équipe de support 🧑‍💻.\nNous vous prions de réessayer d'ici peu. Merci de votre compréhension. 💙"
    ],
    "unsaved_fallback": "⚠️ Désolé, votre retour n'a pas été sauvegardé.`\n Veuillez continuer. 😊",
    "affirm_without_discussion": "Oopsy, 🙃\nVous êtes sur un Flux incorrect 😅!\n🔄 Merci de préciser votre demande.🌹",
    "unexpected_response": "Désolé, 😅!\n🔄 Merci de me confirmer votre demande.🌹",
    "follow_my_proposition": "🚫 Oopsy, Réponse inattendue 🙃\nVous êtes sur un Flux incorrect 😅!\n🔄 Merci de bien répondre à ma proposition.🌹",
    "technical_problem_error": "🚨 Un problème technique est survenu. Notre équipe technique a été notifiée.",
    "technical_problem_exception": "🚩 Désolé, une erreur inattendue s'est produite. L'équipe technique a été alertée.",
    "fallback_message": "*🤔 Oopsy, j’ai zappé le sens là.*\n*🔄 Merci de clarifier votre insertion et de chequer s'il y a eu des typos 🧐.*\n*On va y arriver ensemble 🚀.*",
    "no_response": "🙏 Désolé, je n’ai pas trouvé de réponse adaptée !",
    "no_composante": "Oopsy, 🙃\ncette **Composante/Sous-Sous Composante** est inexistante 😅!\n🔄 Merci de chequer s'il y a eu des typos 🧐.\n",
    "thanks_for_your_feedback": "🙏 Merci pour votre retour",
    "confirm_before_auth": "⚠️ Nous vous remercions de bien vouloir confirmer **avant** de nous communiquer vos identifiants 😊 !",
    "login_required": "👍 D'accord.\nMerci de me fournir 🔐 votre **Nom d'utilisateur** et votre **Mot de Passe** via le formulation ci-dessous :",
    "not_connected": "⛔ Vous n'êtes pas connectés à votre compte !\nMerci d'insérer votre **Nom utilisateur** et votre **Mot de passe** 🗝️.",
    "not_authorized_user": "⛔ Désolé, vous n'êtes pas autorisé à ce service.\n\uD83D\uDD10 Les résultats du passage de grade sont **réservés** aux candidats.",
    "missed_deposit": "⚠️ Note Inexistante car Vous **n'avez pas déposé** aucun document pour ",
    "result_not_found": "😔 Désolé,\n⚠️ Aucun résultat n'est disponible !\n- La validation de votre Dépôt n'est pas encore finalisée par les Évaluateurs. \n- **Ou** vous n'avez pas dépposé vos documents !. \nMerci pour votre compréhension 🌹",
    "all_comp_mark": "📝 Note Composante Principale :\n",
    "sscomp_comp_mark": "📝 Note(s) Sous Sous Composante(s) :\n",
    "unexpected_error": "❌ Désolé, une erreur inattendue s'est produite.",
    "good_reception": "Bonne Réception 🌹",
    "official_tech_problem": "❌ Désolé, un problème technique est survenu.",
    "circuit_opened_alert": "🥺 Désolé, plusieurs tentatives incorrectes ont été trackées !\nVous êtes invités à réessayer dans 120 secondes. ⏳",
    "prompt_input_username": "⚠️ Veuillez entrer votre nom d'utilisateur :",
    "prompt_input_access_id": "⚠️ Veuillez entrer votre mot de passe :",
    "many_attempts": "🛑 Plusieurs tentatives de connexion ont été échouées. \n⏳ Je vous invite à réessayer dans ",
    "skip_duplication": "🛑   Skipping duplicate execution of same action with ",
    "to_be_fixed_by_team": "Notre équipe est déjà notifiée 🛠️ et travaille à la résolution.\nVeuillez réessayer ultérieurement. Merci de votre patience !",
    "no_eval_grid_exist": "Oopsy ! 😬\n🔗 Il n'existe aucune Grille d'évaluation pour le moment !",
    "want_to_know_more": "\n 🤔 Envie de savoir plus ? choisissez simplement une autre **Sous-Sous Composante** :",
    "skip_unrelated_action": "⛔ ⛔ ⛔ Skipped Execute unrelated Action : DOESN'T written in rules.yml + Self Triggered By Rasa !.",
    "skip_little_question": "😅 Trop court !\n 🔄 Pouvez-vous reformuler votre question ?",
    "skip_long_question": f"Oupsy 😅, ton message est un peu trop long.\nMerci de reformuler votre question plus brièvement *({settings.MAX_USER_QUESTION_WORDS} mots)* 🙏",
    "error_model_connexion": "🔌 Erreur de connexion au modèle.",
    "typo_in_qe": "🤔 Désolé, votre question est non claire.\n\n Merci de chequer s'il y a eu des typos !",
    "huge_llm_response_time": "😔 Désolé, le modèle a mis trop de temps à répondre.\n Merci d'essayer plus tard !",
    "model_call_error": "Erreur interne lors de l'appel au modèle",
    "no_context_found": "Désolé 😬 , \nJe n'ai pas trouvé d'information fiable pour répondre à cette question.",
    "no_sscomp_found": "⛔ Composante non pas existante\nMerci de vérifier s'il y a eu des typos.",
    "only_french": "Désolé, 🙏\nPour le moment, la discussion est disponible uniquement en Français.\nEssayer de vérifier s'il y a eu des typos.\nNote : 🌍 Le mode multilingue est une fonctionnalité que nous prévoyons d'ajouter prochainement.",
    "no_expert_found": "🤔 Désolé, Cette Personne ne figure pas dans la liste actuelle des experts (Évaluateurs ou Jurys).\n Merci de chequer s'il y a eu des typos 🔍 !",
    "free_tokens_reached": "🚩 Désolé,\n Le service IA est temporairement indisponible.\nVeuillez reéssayer ultérieurement ⌛.\n",
    "affirm_no_result": "Super ! 🎉😊\nJe suis là si tu as besoin de quoi que ce soit d'autre 💖🙌"
}

INTENT_MAP_PG_INFO = {
    ActiveIntents.GIVE_DATE_BY_COMP.value: settings.PATH_HIERARCY_DATE,
    ActiveIntents.GIVE_DURATION_BY_COMP.value: settings.PATH_HIERARCY_DURATION,
    ActiveIntents.GIVE_PLACE_BY_COMP.value: settings.PATH_HIERARCY_PLACE,
    ActiveIntents.GIVE_DELIVERY_KIND_BY_COMP.value: settings.PATH_HIERARCY_EXAM_KIND,
    ActiveIntents.GIVE_SCORE_BY_COMP.value: settings.PATH_HIERARCY_SCORE
}

# SPECIAITIES
EM_SPEC = "électromécanique"
GED_SPEC = "génie énergétique développement durable"
LCOM_SPEC = "langues & communication"
TIC_SPEC = "technologies de l'information"
GC_SPEC = "génie civil"
MATH_SPEC = "mathématiques"

# GRADES
EFA_GRAD = "enseignant formateur associé"
EFS_GRAD = "enseignant formateur sénior"
EFM_GRAD = "enseignant formateur manager"
EF_GRAD = "enseignant formateur"

AT_GRAD = "Assistant Technologue"
MT_GRAD ="Maître Technologue"
PT_GRAD = "Professeur Technologue"
T_GRAD = "Technologue"

ELCC1_GRAD = "enseignant de langue, de communication et de citoyenneté classe 1"
ELCC2_GRAD = "enseignant de langue, de communication et de citoyenneté classe 2"
ELCC_GRAD = "enseignant de langue, de communication et de citoyenneté"

PAC2_GRAD = "Professeur Agrégé Classe 2",
PAC1_GRAD = "Professeur Agrégé Classe 1",
PA_GRAD = "Professeur Agrégé"

# COMPOSANTES
FIRST_COMP = "Connaissance de Base"
SECOND_COMP = "Production"
THIRD_COMP = "Dossier & Entretien"

DOSS_SSCOMP = "Dossier"
RDI_SSCOMP = "Production RDI"
PP_SSCOMP = "Production Pédagogiques"
CP_SSCOMP = "Capsules Pédagogiques"
SP_SSCOMP = "Supports Pédagogiques"
QCM_SSCOMP = "Test QCM"
PD_SSCOMP = "Présentation de Dossier"
DJ_SSCOMP = "Discussion avec Jury"
DISSER_SSCOMP = "Dissertations"
SE_SSCOMP = "Séquence d'Enseignement"
PTP_SSCOMP = "Plateforme de TP"
EJ_SSCOMP = "Entretien Avec Jury"
ElJ_SSCOMP = "Entretien avec le Jury"
SE_PTP_SSCOMP = "Séquence d'Enseignement OU Plateforme de TP"

# SESSIONS
Y2425_SESSION = "session de passage de grade 2024-2025"
Y2526_SESSION = "session de passage de grade 2025-2026"

# HELPERS
FLAG_ALERT = "🚩 🚩 🚩 🚩 🚩 🚩 🚩 🚩"
DIRECT_HAND_LONG = "👉   👉   👉   👉   👉   👉   👉   👉   👉   👉   👉   👉   👉   👉   👉   👉   👉  "
DIRECT_HAND_FLAG = "👉   👉   👉   "
GO_SHORT = "  GO -  S H O R T"
GO_DETAILS = "  GO -  D E T A I L S"

