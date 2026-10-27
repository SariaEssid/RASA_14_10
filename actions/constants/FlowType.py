"""
actions/constants/FlowType.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from enum import Enum

class FlowType(str, Enum):
    NOTE_FIRST_COMP = "note_first_comp"
    NOTE_SECOND_COMP = "note_second_comp"
    NOTE_THIRD_COMP = "note_third_comp"
    NOTE_TEST_QCM = "note_test_qcm"
    NOTE_SUPP_PEDA = "note_supp_peda"
    NOTE_PROD_RDI = "note_prod_rdi"
    NOTE_EVAL_PRES_SE = "note_eval_pres_se"
    NOTE_EVAL_SE = "note_eval_se"
    NOTE_EVAL_PRES_PTP = "note_eval_pres_ptp"
    NOTE_EVAL_PTP = "note_eval_ptp"
    NOTE_PRES_DOSS = "note_pres_doss"
    NOTE_DISS_JURY = "note_diss_jury"
    NOTE_DOSS = "note_doss"
    NOTE_QCM_ALL = "note_qcm_all"
    NOTE_CAPS_PEDA_ALL = "note_caps_peda_all"
    NOTE_DISS_ALL = "note_diss_all"
    NOTE_SEQ_ENS_ALL = "note_seq_ens_all"
    NOTE_PLAT_TP_ALL = "note_plat_tp_all"
    NOTE_PROD_PEDA_ALL = "note_prod_peda_all"
    NOTE_ENTR_JURY_ALL = "note_entr_jury_all"
    NOTE_CAPS_EN = "note_caps_en"
    NOTE_DISS_FR = "note_diss_fr"
    NOTE_CAPS_FR = "note_caps_fr"
    NOTE_DISS_EN = "note_diss_en"
    DELIBERATION = "deliberation"
    CONGRATS = "congrats"
    ALL_BILAN = "all_bilan"
    RESULT = "result"
    GREET = "greet"
    BYE = "bye"
    GUIDE_COMP = "guide_comp"
    GIVE_ADVICE_1 = "give_advice_1"
    GIVE_ADVICE_2 = "give_advice_2"
    GIVE_ADVICE_3 = "give_advice_3"
    SELECTED_COMP = "selected_comp"
    SELECTED_ADVICE_PLAN = "selected_advice_plan"
    SELECTED_DIRECTION_ADVICE_PLAN = "selected_advice_plan"
    DUMMY_FLOW = "dummy_flow"
    EVALUATION_GRID = "eval_grid"

    def __str__(self):
        return self.value

SSCOMP_TO_FLOW = {
    "first_comp": FlowType.NOTE_FIRST_COMP,
    "second_comp": FlowType.NOTE_SECOND_COMP,
    "third_comp": FlowType.NOTE_THIRD_COMP,
    "test_qcm": FlowType.NOTE_TEST_QCM,
    "supp_peda": FlowType.NOTE_SUPP_PEDA,
    "prod_rdi": FlowType.NOTE_PROD_RDI,
    "eval_pres_se": FlowType.NOTE_EVAL_PRES_SE,
    "eval_se": FlowType.NOTE_EVAL_SE,
    "eval_pres_ptp": FlowType.NOTE_EVAL_PRES_PTP,
    "eval_ptp": FlowType.NOTE_EVAL_PTP,
    "pres_doss": FlowType.NOTE_PRES_DOSS,
    "diss_jury": FlowType.NOTE_DISS_JURY,
    "doss": FlowType.NOTE_DOSS,
    "qcm_all": FlowType.NOTE_QCM_ALL,
    "caps_peda_all": FlowType.NOTE_CAPS_PEDA_ALL,
    "diss_all": FlowType.NOTE_DISS_ALL,
    "seq_ens_all": FlowType.NOTE_SEQ_ENS_ALL,
    "plat_tp_all": FlowType.NOTE_PLAT_TP_ALL,
    "prod_peda_all": FlowType.NOTE_PROD_PEDA_ALL,
    "entr_jury_all": FlowType.NOTE_ENTR_JURY_ALL
}

INTENT_TO_FLOW = {
    "ask_about_candidature_passage_grade": FlowType.GUIDE_COMP,
    "stressed_candidat": FlowType.SELECTED_ADVICE_PLAN,
    "select_comp_for_guide": FlowType.SELECTED_COMP,
    "affirm_advice_1": FlowType.GIVE_ADVICE_1,
    "affirm_advice_2": FlowType.GIVE_ADVICE_2,
    "affirm_advice_3": FlowType.GIVE_ADVICE_3,
    "ask_criteres_evaluation_sscomp" : FlowType.EVALUATION_GRID
}