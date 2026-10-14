"""
actions/constants/ActiveIntents.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from enum import Enum

class ActiveIntents(str, Enum):
    ASK_RESULTAT_DISSERTATION = "ask_resultat_dissertation"
    ASK_RESULTAT_CAPSULE = "ask_resultat_capsule"
    ASK_RESULTAT_SSCOMP = "ask_resultat_sscomp"
    ASK_RESULTAT_FINAL = "ask_resultat_final"
    ASK_STATUS_DELIBERATION_RESULTAT = "ask_status_deliberation_result"
    PROVIDE_CREDENTIALS = "provide_credentials"
    ASK_DENY = "deny"
    ASK_AFFIRM = "affirm"
    ASK_ABOUT_CANDIDATURE_PASSAGE_GRADE = "ask_about_candidature_passage_grade"
    STRESSED_CANDIDAT = "stressed_candidat"
    SELECT_COMP_FOR_GUIDE = "select_comp_for_guide"
    AFFIRM_ADVICE_1 = "affirm_advice_1"
    AFFIRM_ADVICE_2 = "affirm_advice_2"
    AFFIRM_ADVICE_3 = "affirm_advice_3"
    ASK_CRITERES_EVALUATIONS_SSCOMP = "ask_criteres_evaluation_sscomp"
    ASK_NORMAL_EXCEPTIONAL_METRIX = "ask_normal_exceptional_metrics"
    TOO_LONG_INPUT = "too_long_input"
    GIVE_COMP_HIERARCHY = "give_comp_hierarchy"
    GIVE_DATE_BY_COMP = "give_date_by_comp"
    GIVE_DURATION_BY_COMP = "ask_duration_exam" #"give_duration_by_comp"
    GIVE_PLACE_BY_COMP = "ask_place_examen" #"give_place_by_comp"
    GIVE_DELIVERY_KIND_BY_COMP = "ask_types_livrables" #"give_delivery_kind_by_comp"
    GIVE_SCORE_BY_COMP = "give_score_by_comp"
    ASK_GLOBAL_ADVICES_PG = "ask_global_advices_pg"
    ASK_GRANULAR_ADVICES_PG = "ask_granular_advices_pg"
    ASK_PLAGIARISM = "ask_plagiarism"
    ASK_PROCEDURE_PG = "ask_procedure_pg"
    ASK_MOODLE = "ask_moodle"
    ASK_EVAL_VS_PJ = "ask_eval_vs_pj",
    ASK_EXPERT_BY_SPEC_COMP = "ask_expert_by_spec_comp",
    ASK_INFOS_EXPERT_BY_NAME = "ask_infos_expert_by_name"
    ASK_CONCERNED_GRADES = "ask_concerned_grades"
    ASK_SUCCESS_RATE = "ask_success_rate"
    HOW_AUTHENTICATE_WITH_CHATBOT = "how_authenticate_with_chatbot"
    ASK_NBR_NEEDED_POSITIONS_BY_SPEC = "ask_nbr_needed_positions_by_spec"
    PRESENT_ACADEMIC_STUFF = "present_academic_stuff"
    NLU_FALLBACK = "nlu_fallback"
    ASK_MULTILINGUAL_MODE = "ask_multilingual_mode"
    ASK_MODIFY_PROFILE_PHOTO = "ask_modify_profile_photo"
    ASK_ABOUT_COMP = "ask_about_comp"
    ASK_ACCESS_RESOURCES_BY_EVALUATOR = "ask_access_resources_by_evaluator"
    ASK_UPDATE_PERSONAL_INFORMATION = "ask_update_personal_information"
    ASK_LINK_VIDEO_DRIVE_IN_PDF = "ask_link_video_drive_in_pdf"
    ASK_ATTACH_PROOFS = "ask_attach_proofs"
    ASK_TOO_LONG_INPUT = "too_long_input"
    PRESENT_PGPG_PLATEFORM = "present_pgpg_platform"
    ASK_DEMANDE_REEVALUATION = "ask_demande_reevaluation"
    ASK_HANDLE_AUTOMATIC_EVALUATION = "ask_handle_automatic_evaluations"
    ASK_ABOUT_ESB = "ask_about_esb"
    ASK_FORGOT_RESET_PASSWORD = "ask_forgot_reset_password"
    ASK_CHANGE_PASSWORD = "ask_change_password"
    ASK_WHO_MANAGE_SESSIONS = "ask_who_manage_sessions"
    ASK_HOW_MANAGE_SESSIONS = "ask_how_manage_sessions"
    ASK_OLD_VS_NEW_GRADES = "ask_old_vs_new_grades"
    ASK_ROLE_RH = "ask_role_rh"
    ASK_PRESENT_SARIA_ESSID = "ask_present_essid_saria"

    def __str__(self):
        return self.value

    ALL_ENTRY_INTENTS = [
        "greet",
        "bye",
        "present_academic_stuff",
        "ask_about_esb",
        "ask_concerned_grades",
        "ask_nbr_needed_positions_by_spec",
        "ask_place_examen",
        "ask_candidats_elligibles_anciennete",
        "ask_types_livrables",
        "ask_modify_deposit",
        "ask_notify_candidat",
        "ask_renew_session_pg",
        "ask_fees_inscription",
        "ask_make_up_session",
        "ask_success_candidat",
        "ask_failure_candidat",
        "ask_criteres_evaluation_sscomp",
        "ask_duration_exam",
        "reclam_no_typo",
        "ask_link_video_drive_in_pdf",
        "ask_confidentialite_delivrables",
        "ask_equality_mesures",
        "ask_change_password",
        "ask_about_candidature_passage_grade",
        "ask_forgot_reset_password",
        "ask_success_rate",
        "ask_select_evaluator_jury",
        "ask_attach_proofs",
        "ask_role_cpgr",
        "ask_ranking_esprit",
        "give_comp_hierarchy",
        "give_date_by_comp",
        "ask_global_advices_pg",
        "ask_granular_advices_pg",
        "give_score_by_comp",
        "ask_reference_period",
        "ask_level_publication",
        "ask_normal_exceptional_metrics",
        "ask_access_resources_by_evaluator",
        "ask_update_personal_information",
        "ask_request_support_contact",
        "ask_workflow_evaluation",
        "ask_handle_automatic_evaluations",
        "ask_view_academic_comments",
        "ask_demande_reevaluation",
        "ask_historique_evaluation",
        "ask_offline_mode",
        "ask_multilingual_mode",
        "ask_present_essid_saria",
        "ask_esprit_dsi_ai",
        "too_long_input",
        "ask_eval_vs_pj",
        "ask_expert_by_spec_comp",
        "ask_infos_expert_by_name"
    ]

    ALL_CUSTOM_INTENTS = [
        "present_academic_stuff",
        "ask_about_esb",
        "ask_concerned_grades",
        "ask_nbr_needed_positions_by_spec",
        "ask_place_examen",
        # "ask_candidats_elligibles_anciennete",
        "ask_types_livrables",
        # "ask_notify_candidat",
        # "ask_renew_session_pg",
        # "ask_fees_inscription",
        # "ask_make_up_session",
        # "ask_success_candidat",
        # "ask_failure_candidat",
        "ask_criteres_evaluation_sscomp",
        "ask_duration_exam",
        # "reclam_no_typo",
        "ask_link_video_drive_in_pdf",
        "ask_confidentialite_delivrables",
        # "ask_equality_mesures",
        "ask_change_password",
        "ask_about_candidature_passage_grade",
        "ask_forgot_reset_password",
        "ask_success_rate",
        # "ask_select_evaluator_jury",
        "ask_attach_proofs",
        # "ask_role_cpgr",
        "ask_ranking_esprit",
        "give_comp_hierarchy",
        "give_date_by_comp",
        "ask_global_advices_pg",
        "ask_granular_advices_pg",
        "give_score_by_comp",
        "ask_level_publication",
        "ask_normal_exceptional_metrics",
        "ask_access_resources_by_evaluator",
        "ask_update_personal_information",
        "ask_handle_automatic_evaluations",
        "ask_demande_reevaluation",
        "ask_offline_mode",
        "ask_multilingual_mode",
        "ask_present_essid_saria",
        "ask_esprit_dsi_ai",
        "too_long_input",
        "ask_eval_vs_pj",
        "ask_expert_by_spec_comp",
        "ask_infos_expert_by_name"
    ]

    ALL_LLM_INTENTS_LANG_CHAIN = [
        "ask_offline_mode",
        "ask_multilingual_mode",
        "ask_present_essid_saria",
        "present_pfe_platform",
        "present_pgpg_platform",
        "ask_about_esb",
        "ask_ranking_esprit",
        "ask_esprit_dsi_ai",
        "ask_forgot_reset_password",
        "ask_handle_automatic_evaluations",
        "ask_change_password",
        "how_authenticate_with_chatbot",
        "ask_procedure_pg",
        "ask_moodle",
        "ask_who_manage_sessions",
        "ask_how_manage_sessions",
        "ask_old_vs_new_grades",
        "ask_role_rh",
        "ask_plagiarism",
        "too_long_input",
        "ask_link_video_drive_in_pdf",
        "ask_global_advices_pg",
        "ask_granular_advices_pg",
        "ask_normal_exceptional_metrics",
        "ask_modify_profile_photo",
        "ask_about_comp",
        "ask_attach_proofs",
        "ask_access_resources_by_evaluator",
        "ask_update_personal_information",
        "ask_level_publication",
        "ask_demande_reevaluation",
        "give_comp_hierarchy"
    ]

    ALL_LLM_INTENTS_LANG_CHAIN_EXTEND = [
        "ask_present_essid_saria",
        "ask_about_esb",
        "ask_ranking_esprit",
        "ask_esprit_dsi_ai",
        "ask_forgot_reset_password",
        "ask_change_password",
        "how_authenticate_with_chatbot",
        "ask_moodle",
        "ask_who_manage_sessions",
        "ask_how_manage_sessions",
        "ask_old_vs_new_grades",
        "ask_role_rh",
        "ask_plagiarism",
        "ask_procedure_pg",
        "too_long_input",
        "present_pfe_platform",
        "present_pgpg_platform",
        "ask_global_advices_pg",
        "ask_granular_advices_pg",
        "ask_normal_exceptional_metrics",
        "ask_modify_profile_photo",
        "ask_about_comp",
        "ask_access_resources_by_evaluator",
        "ask_attach_proofs",
        "ask_update_personal_information",
        "ask_level_publication",
        "ask_demande_reevaluation",
        "ask_handle_automatic_evaluations",
        "select_comp_for_guide"
    ]

    ALL_LLM_INTENTS_PG_INFOS = [
        "ask_place_examen",
        "ask_duration_exam",
        "give_date_by_comp",
        "give_score_by_comp",
        "ask_types_livrables"
    ]

    # "nlu_fallback"  15-04-2026
    RESULTS_INTENTS=[
        "ask_resultat_dissertation",
        "ask_resultat_capsule",
        "ask_resultat_sscomp",
        "ask_resultat_final",
        "ask_status_deliberation_result",
        "give_advice_1",
        "give_advice_2",
        "give_advice_3",
        "how_authenticate_with_chatbot",
        "affirm"
    ]

    NO_AFFIRM_INTENTS = [
        "ask_resultat_dissertation",
        "ask_resultat_capsule",
        "ask_resultat_sscomp",
        "ask_resultat_final",
        "ask_status_deliberation_result",
        "how_authenticate_with_chatbot",
        "give_advice_1",
        "give_advice_2",
        "give_advice_3",
        "stressed_candidat",
        "affirm"
    ]

    SKIP_FROM_ENTRY_INTENTS = [
        "ask_global_advices_pg",
        "ask_granular_advices_pg",
        "give_date_by_comp",
        "give_comp_hierarchy",
        "ask_duration_exam",
        "ask_place_examen",
        "ask_types_livrables",
        "ask_concerned_grades",
        "ask_nbr_needed_positions_by_spec",
        "ask_success_rate",
        "nlu_fallback"
    ]

    ALL_STATIC_INTENTS = [
        "ask_candidats_elligibles_anciennete",
        "ask_modify_deposit",
        "ask_notify_candidat",
        "ask_renew_session_pg",
        "ask_fees_inscription",
        "ask_make_up_session",
        "ask_success_candidat",
        "ask_failure_candidat",
        "ask_equality_mesures",
        "reclam_no_typo",
        "ask_select_evaluator_jury",
        "ask_role_cpgr",
        "ask_reference_period",
        "ask_request_support_contact",
        "ask_workflow_evaluation",
        "ask_view_academic_comments",
        "ask_historique_evaluation",
        "stressed_candidat"
    ]

    ALL_JSON_INTENTS = [
        "ask_success_rate",
        "ask_concerned_grades",
        "ask_nbr_needed_positions_by_spec"
    ]

    ALL_FILE_INTENTS = [
        "ask_place_examen",
        "ask_duration_exam",
        "give_date_by_comp",
        "give_score_by_comp",
        "ask_types_livrables",
        "ask_success_rate",
        "ask_concerned_grades",
        "ask_nbr_needed_positions_by_spec"
    ]

    ALL_EXPERTS_INTENTS = [
        "ask_eval_vs_pj",
        "ask_expert_by_spec_comp",
        "ask_infos_expert_by_name"
    ]

    FALLBACK_INTENTS = [
        "nlu_fallback"
    ]

    MUTED_INTENTS = [
        "greet",
        "bye",
        "affirm",
        "deny",
        "affirm_helpful",
        "deny_helpful"
    ]

    NO_FOLLOW_UP_INTENTS = [
        "greet",
        "bye",
        "affirm",
        "deny"
    ]

    EXCEPTED_INTENTS_FROM_RESP_FORMAT = [
        "give_comp_hierarchy",
        "ask_procedure_pg",
    ]

    MANAGE_PWDS_INTENTS = [
        "ask_forgot_reset_password",
        "ask_change_password",
    ]

    ALL_DELIBERATION_INTENTS = [
        "ask_status_deliberation_result",
        "how_authenticate_with_chatbot"
    ]