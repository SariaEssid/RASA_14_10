"""
tests/unit/test_http_auth_and_jwt.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import pytest
from httpx import HTTPError

from actions.utils.services import HttpResultsService
from tests.utils.constants import USER_1_TOKEN, USER_1_ID


@pytest.mark.asyncio
async def test_jwt_validation_failure(monkeypatch):

    service = HttpResultsService()

    async def fake_validate(_token=None):
        return False

    monkeypatch.setattr(
        "actions.utils.services._validate_jwt_before_request",
        fake_validate
    )

    with pytest.raises(RuntimeError):
        await service.get_candidate_results(USER_1_ID, USER_1_TOKEN)

@pytest.mark.asyncio
async def test_jwt_invalid(monkeypatch):
    service = HttpResultsService()

    async def bad(*_args, **_kwargs):
        return False

    monkeypatch.setattr(
        "actions.utils.services._validate_jwt_before_request",
        bad
    )

    with pytest.raises(RuntimeError):
        await service.get_candidate_results(USER_1_ID, USER_1_TOKEN)


@pytest.mark.asyncio
async def test_jwt_none(monkeypatch):
    service = HttpResultsService()

    async def none(*_args, **_kwargs):  # Adding *args, **kwargs makes it flexible
        return None

    monkeypatch.setattr(
        "actions.utils.services._validate_jwt_before_request",
        none
    )

    with pytest.raises(RuntimeError):
        await service.get_candidate_results(USER_1_ID, USER_1_TOKEN)