"""
tests/unit/test_log_type.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.constants.LogType import LogType


def test_log_type_values():
    """Verify that enum members hold the expected string values."""
    assert LogType.TYPE_EXCEPTION == "EXCEPTION"
    assert LogType.TYPE_INFO == "INFO"


def test_log_type_string_representation():
    """Verify that the custom __str__ method returns the underlying value."""
    assert str(LogType.TYPE_EXCEPTION) == "EXCEPTION"
    assert str(LogType.TYPE_INFO) == "INFO"


def test_log_type_string_inheritance():
    """Verify that LogType instances behave as strings due to str, Enum inheritance."""
    assert isinstance(LogType.TYPE_EXCEPTION, str)
    assert LogType.TYPE_EXCEPTION.lower() == "exception"


def test_log_type_membership():
    """Verify all expected enum members are present."""
    members = {member.name for member in LogType}
    assert members == {"TYPE_EXCEPTION", "TYPE_INFO"}