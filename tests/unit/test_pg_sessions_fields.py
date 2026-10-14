"""
tests/unit/test_pg_sessions_fields.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

from actions.constants.PGSessionsFields import PGSessionsFields

def test_pg_sessions_fields_values():
    """Verify that all enum members hold the expected string values."""
    assert PGSessionsFields.EN_ATTENTE == "EN_ATTENTE"
    assert PGSessionsFields.DISPONIBLE == "DISPONIBLE"
    assert PGSessionsFields.EN_COURS == "EN_COURS"
    assert PGSessionsFields.ARCHIVEE == "ARCHIVEE"
    assert PGSessionsFields.RATE_FIELD == "results_by_sessions"
    assert PGSessionsFields.POSITIONS_FIELD == "specialites_by_sessions"
    assert PGSessionsFields.GRADES_FIELD == "sessions"


def test_pg_sessions_fields_string_representation():
    """Verify that the custom __str__ method returns the exact underlying value."""
    assert str(PGSessionsFields.EN_ATTENTE) == "EN_ATTENTE"
    assert str(PGSessionsFields.RATE_FIELD) == "results_by_sessions"


def test_pg_sessions_fields_string_inheritance():
    """Verify that instances inherit from str and support string operations."""
    assert isinstance(PGSessionsFields.DISPONIBLE, str)
    assert PGSessionsFields.DISPONIBLE.lower() == "disponible"


def test_pg_sessions_fields_membership():
    """Verify that all expected enum members are present."""
    members = {member.name for member in PGSessionsFields}
    expected_members = {
        "EN_ATTENTE",
        "DISPONIBLE",
        "EN_COURS",
        "ARCHIVEE",
        "RATE_FIELD",
        "POSITIONS_FIELD",
        "GRADES_FIELD",
    }
    assert members == expected_members