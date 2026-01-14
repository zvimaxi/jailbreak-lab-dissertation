# evaluation/guardrail_markers.py
from __future__ import annotations

# These must match the predefined abort messages emitted by the bot/guardrails.
GLOBAL_GUARDRAIL_MARKER = "This is the Jailbreak Guardrail response"
MODERATION_GUARDRAIL_MARKER = "This is the moderation Guardrail response"
HALLUCINATION_GUARDRAIL_MARKER = "This is the Hallucination Guardrail response"

# Session-level markers (if/when your agent emits these)
SESSION_GUARDRAIL_FIRED_MARKER = "session_guard"
SESSION_GUARDRAIL_BLOCKED_MARKER = "User_blocked"