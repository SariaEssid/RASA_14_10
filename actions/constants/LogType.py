"""
actions/constants/LogType.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from enum import Enum

class LogType(str, Enum):

    TYPE_EXCEPTION = "EXCEPTION"
    TYPE_INFO = "INFO"

    def __str__(self):
        return self.value