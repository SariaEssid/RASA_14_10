"""
actions/constants/PGSessionsFields.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from enum import Enum

class PGSessionsFields(str, Enum):
    EN_ATTENTE = "EN_ATTENTE"
    DISPONIBLE = "DISPONIBLE"
    EN_COURS = "EN_COURS"
    ARCHIVEE = "ARCHIVEE"
    RATE_FIELD = "results_by_sessions"
    POSITIONS_FIELD = "specialites_by_sessions"
    GRADES_FIELD = "sessions"

    def __str__(self):
        return self.value