# tests/unit/test_logger.py
import pytest
from unittest.mock import AsyncMock, patch
from actions.logging import logger as lg

def test_redact_secrets():
    assert "SECRET" not in lg.redact_secrets("username = X ; password = SECRET")
    assert "SECRET" not in lg.redact_secrets("mon mot de passe est SECRET")
    assert lg.redact_secrets("comment réinitialiser mon mot de passe ?") == \
           "comment réinitialiser mon mot de passe ?"

def test_sanitize_payload_nested():
    out = lg.sanitize_payload({"password": "x", "userInput": "mdp: SECRET", "n": {"jwt": "t"}})
    assert out == {"userInput": "mdp: [REDACTED]", "n": {}}

@pytest.mark.asyncio
async def test_notify_sends_sanitized_payload():
    with patch.object(lg, "post_to_backend", new=AsyncMock(return_value=True)) as m:
        await lg.notify_team_leader_by_technical_problem(
            {"username": "u", "password": "SECRET", "userInput": "password=SECRET"})
    sent = m.call_args.args[1]
    assert "SECRET" not in str(sent)