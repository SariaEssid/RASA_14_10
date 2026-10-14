"""
tests/unit/test_call_llm.py

@author ESSID Saria | Copyright (c) 2025. ESPRIT
"""

import pytest

from actions.actions import call_llm_with_retry


class DummyDispatcher:
    def utter_message(self, *_args, **_kwargs):
        pass


@pytest.mark.asyncio
async def test_call_llm_success():

    async def fake_llm(_prompt, _temperature):
        return "ok"

    result = await call_llm_with_retry(
        fake_llm,
        DummyDispatcher(),
        "hello",
        "ACTION",
        {}
    )

    assert result == "ok"


@pytest.mark.asyncio
async def test_call_llm_timeout_then_success():

    calls = {"n": 0}

    async def fake_llm(_prompt, _temperature):
        calls["n"] += 1

        if calls["n"] == 1:
            raise TimeoutError("timeout")

        return "recovered"

    result = await call_llm_with_retry(
        fake_llm,
        DummyDispatcher(),
        "hello",
        "ACTION",
        {}
    )

    assert result == "recovered"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_call_llm_timeout_then_failure(monkeypatch):

    async def fake_llm(_prompt, _temperature):
        raise TimeoutError("timeout")

    monkeypatch.setattr(
        "actions.actions.exception_fallback_err",
        lambda _dispatcher: "fallback"
    )

    monkeypatch.setattr(
        "actions.actions.exception_fallback_err_dsi",
        lambda *_args, **_kwargs: None
    )

    with pytest.raises(RuntimeError, match="fallback"):
        await call_llm_with_retry(
            fake_llm,
            DummyDispatcher(),
            "hello",
            "ACTION",
            {}
        )


@pytest.mark.asyncio
async def test_call_llm_generic_exception(monkeypatch):

    async def fake_llm(_prompt, _temperature):
        raise ValueError("boom")

    monkeypatch.setattr(
        "actions.actions.exception_llm_err",
        lambda _dispatcher: "llm-error"
    )

    monkeypatch.setattr(
        "actions.actions.exception_llm_err_dsi",
        lambda *_args, **_kwargs: None
    )

    with pytest.raises(RuntimeError, match="llm-error"):
        await call_llm_with_retry(
            fake_llm,
            DummyDispatcher(),
            "hello",
            "ACTION",
            {}
        )