"""
actions/constants/EntitiesMapping.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""
from actions.constants.Constants import EM_SPEC, GED_SPEC, LCOM_SPEC, TIC_SPEC, GC_SPEC, MATH_SPEC, EFA_GRAD, EFS_GRAD, \
    EFM_GRAD, EF_GRAD, AT_GRAD, MT_GRAD, PT_GRAD, T_GRAD, ELCC1_GRAD, ELCC2_GRAD, ELCC_GRAD, PAC2_GRAD, PAC1_GRAD, \
    PA_GRAD, DOSS_SSCOMP, FIRST_COMP, SECOND_COMP, THIRD_COMP, RDI_SSCOMP, PP_SSCOMP, SP_SSCOMP, QCM_SSCOMP, \
    PD_SSCOMP, DJ_SSCOMP, DISSER_SSCOMP, SE_SSCOMP, PTP_SSCOMP, EJ_SSCOMP, CP_SSCOMP, SE_PTP_SSCOMP, ElJ_SSCOMP, \
    Y2425_SESSION, Y2526_SESSION

SPEIALITIES_LABELS = {
    "elct_mkn": f"{EM_SPEC}",
    "ged": f"{GED_SPEC}",
    "lcom": f"{LCOM_SPEC}",
    "tic": f"{TIC_SPEC}",
    "gc": f"{GC_SPEC}",
    "math": f"{MATH_SPEC}",
}

EXPERTS_LABELS = {
    "abderrazek_hachani": "Abderrazek Hachani",
    "adel_brik": "Adel Brik",
    "ahmed_makki_latrech": "Ahmed Makki Latrech",
    "asma_karoui": "Asma Karoui",
    "belhassen_guettat": "Belhassen Guettat",
    "chokri_chaaraoui": "Chokri Chaaraoui",
    "douha_arfeoui": "Dhouha Arfeoui",
    "hajer_berhouma": "Hajer Berhouma",
    "imen_guebebia": "Imen Guebebia",
    "imen_kochbati": "Imen Kochbati",
    "joseph_hajjeji": "Joseph Hajjeji",
    "mabrouka_dchicha": "Mabrouka Dchicha",
    "maher_jaziri": "Maher Jaziri",
    "maher_mouakher": "Maher Mouakher",
    "manel_medhioub": "Manel Medhioub",
    "med_bouakline": "Mohamed Ali Bouakline",
    "nadia_ajailia": "Nadia Ajailia",
    "najla_rejab": "Najla Rejeb",
    "rahma_bouraoui": "Rahma Bouraoui",
    "rim_alouan": "Rim Alouan",
    "safa_zhioua_cherif": "Safa Zhioua Cherif",
    "sami_montassar": "Sami Montassar",
    "sonia_batis": "Sonia Batis",
    "soumaya_mbarek": "Soumaya Mbarek",
    "taoufik_chaouachi": "Taoufik Chaouachi",
    "yosr_ghozzi": "Yosr Ghozzi"
}

GRADES_LABELS = {
    "efa": f"{EFA_GRAD}",
    "efs": f"{EFS_GRAD}",
    "efm": f"{EFM_GRAD}",
    "ef": f"{EF_GRAD}",
    "assistant_tech": f"{AT_GRAD}",
    "maitre_tech": f"{MT_GRAD}",
    "professeur_tech": f"{PT_GRAD}",
    "technologue": f"{T_GRAD}",
    "elcc1": f"{ELCC1_GRAD}",
    "elcc2": f"{ELCC2_GRAD}",
    "elcc": f"{ELCC_GRAD}",
    "prof_agr_c2": f"{PAC2_GRAD}",
    "prof_agr_c1": f"{PAC1_GRAD}",
    "prof_agr": f"{PA_GRAD}"
}

OFFICIAL_LABELS = {
    "sscomp": {
        "caps_peda_all": f"{CP_SSCOMP}",
        "first_comp": f"{FIRST_COMP}",
        "second_comp": f"{SECOND_COMP}",
        "third_comp": f"{THIRD_COMP}",
        "doss": f"{DOSS_SSCOMP}",
        "prod_rdi": f"{RDI_SSCOMP}",
        "supp_peda": f"{SP_SSCOMP}",
        "test_qcm": f"{QCM_SSCOMP}",
        "pres_doss": f"{PD_SSCOMP}",
        "diss_jury": f"{DJ_SSCOMP}",
        "diss_all": f"{DISSER_SSCOMP}",
        "prod_peda_all": f"{PP_SSCOMP}",
        "seq_ens_all": f"{SE_SSCOMP}",
        "plat_tp_all": f"{PTP_SSCOMP}",
        "entr_jury_all": f"{EJ_SSCOMP}"
    },
    "session": {
        "session_24-25": f"{Y2425_SESSION}",
        "session_25-26": f"{Y2526_SESSION}"
    },
    "speciality": {
        "elct_mkn": f"{EM_SPEC}",
        "ged": f"{GED_SPEC}",
        "lcom": f"{LCOM_SPEC}",
        "tic": f"{TIC_SPEC}",
        "gc": f"{GC_SPEC}",
        "math": f"{MATH_SPEC}"
    },
    "grade": GRADES_LABELS
}

# SPECIALITY - GRADE - SESSION - SSCOMP - LANGUAGE
ALL_ENTITIES_MAPPINGS ={
    "elct_mkn": f"{EM_SPEC}",
    "ged": f"{GED_SPEC}",
    "lcom": f"{LCOM_SPEC}",
    "tic": f"{TIC_SPEC}",
    "gc": f"{GC_SPEC}",
    "math": f"{MATH_SPEC}",
    "efa": f"{EFA_GRAD}",
    "efs": f"{EFS_GRAD}",
    "efm": f"{EFM_GRAD}",
    "ef": f"{EF_GRAD}",
    "assistant_tech": f"{AT_GRAD}",
    "maitre_tech": f"{MT_GRAD}",
    "professeur_tech": f"{PT_GRAD}",
    "technologue": f"{T_GRAD}",
    "elcc1": "enseignant de langue et de communication et de citoyenneté classe 1",
    "elcc2": "enseignant de langue et de communication et de citoyenneté classe 2",
    "elcc": "enseignant de langue et de communication et de citoyenneté",
    "prof_agr_c2": f"{PAC2_GRAD}",
    "prof_agr_c1": f"{PAC1_GRAD}",
    "prof_agr": f"{PA_GRAD}",
    "session_24-25": f"{Y2425_SESSION}",
    "session_25-26": f"{Y2526_SESSION}",
    "caps_peda_all": f"{CP_SSCOMP}",
    "first_comp": f"{FIRST_COMP}",
    "second_comp": f"{SECOND_COMP}",
    "third_comp": f"{THIRD_COMP}",
    "doss": f"{DOSS_SSCOMP}",
    "prod_rdi": f"{RDI_SSCOMP}",
    "supp_peda": f"{SP_SSCOMP}",
    "test_qcm": f"{QCM_SSCOMP}",
    "pres_doss": f"{PD_SSCOMP}",
    "diss_jury": f"{DJ_SSCOMP}",
    "diss_all": f"{DISSER_SSCOMP}",
    "prod_peda_all": f"{PP_SSCOMP}",
    "seq_ens_all": f"{SE_SSCOMP}",
    "plat_tp_all": f"{PTP_SSCOMP}",
    "entr_jury_all": f"{EJ_SSCOMP}",
    "fr": "Français",
    "en": "Anglais"
}

INTENT_CANONICAL = {
    "rdi": f"{RDI_SSCOMP}",
    "pedagogique": f"{CP_SSCOMP}",
    "dossier": f"{DOSS_SSCOMP}",
    "jury": f"{ElJ_SSCOMP}",
    "base": "Connaissances de base",
    "dissertations": f"{DISSER_SSCOMP}",
    "sequence": f"{SE_PTP_SSCOMP}"
}

COMPOSANTE_CANONICAL = {
    "production rdi": f"{RDI_SSCOMP}",
    "capsules pedagogiques": f"{CP_SSCOMP}",
    "dossier": f"{DOSS_SSCOMP}",
    "sequence d'enseignement": f"{SE_PTP_SSCOMP}",
    "entretien avec le jury": f"{ElJ_SSCOMP}",
    "dissertations": f"{DISSER_SSCOMP}",
    "supports pedagogiques": f"{SP_SSCOMP}",
}

ALL_SPECIAITIES =[f"{EM_SPEC}",
    "genie energetique developpement durable",
    f"{LCOM_SPEC}",
    f"{TIC_SPEC}",
    f"{GC_SPEC}",
    f"{MATH_SPEC}"]