"""Tests for domain-agnostic engagement hooks."""

import logging
from typing import cast

from primer_core.orchestrator.hooks import HookContext, HookEvent, HookRegistry


def _context() -> HookContext:
    """Return an opaque context for isolated HookRegistry tests."""
    return cast(HookContext, object())


def test_hook_event_members_match_contract() -> None:
    assert {event.name: event.value for event in HookEvent} == {
        "BEFORE_ENGAGEMENT": "before_engagement",
        "AFTER_ENGAGEMENT": "after_engagement",
        "ON_MASTERY_CHANGE": "on_mastery_change",
        "ON_STRUGGLE_DETECTED": "on_struggle_detected",
        "ON_SESSION_START": "on_session_start",
        "ON_SESSION_END": "on_session_end",
    }


async def test_hook_registry_fires_handlers_in_registration_order() -> None:
    registry = HookRegistry()
    context = _context()
    calls: list[str] = []

    async def first_handler(ctx: HookContext) -> None:
        assert ctx is context
        calls.append("first")

    async def second_handler(ctx: HookContext) -> None:
        assert ctx is context
        calls.append("second")

    registry.register(HookEvent.AFTER_ENGAGEMENT, first_handler)
    registry.register(HookEvent.AFTER_ENGAGEMENT, second_handler)

    await registry.fire(HookEvent.AFTER_ENGAGEMENT, context)

    assert calls == ["first", "second"]


async def test_hook_registry_isolates_handler_failures_and_preserves_order(
    caplog,
) -> None:
    registry = HookRegistry()
    context = _context()
    calls: list[str] = []

    async def first_handler(ctx: HookContext) -> None:
        assert ctx is context
        calls.append("first")

    async def failing_handler(ctx: HookContext) -> None:
        assert ctx is context
        calls.append("failing")
        raise RuntimeError("hook failed")

    async def third_handler(ctx: HookContext) -> None:
        assert ctx is context
        calls.append("third")

    registry.register(HookEvent.AFTER_ENGAGEMENT, first_handler)
    registry.register(HookEvent.AFTER_ENGAGEMENT, failing_handler)
    registry.register(HookEvent.AFTER_ENGAGEMENT, third_handler)

    with caplog.at_level(
        logging.ERROR,
        logger="primer_core.orchestrator.hooks",
    ):
        await registry.fire(HookEvent.AFTER_ENGAGEMENT, context)

    assert calls == ["first", "failing", "third"]

    assert any(
        record.getMessage() == "Hook handler failed for event after_engagement"
        and record.exc_info is not None
        for record in caplog.records
    )


async def test_hook_registry_unregistered_event_is_noop() -> None:
    registry = HookRegistry()
    context = _context()

    await registry.fire(HookEvent.ON_SESSION_END, context)
