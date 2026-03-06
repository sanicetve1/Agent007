"""
Intent Node: understand the user request and extract intent + entities.

If a required entity (e.g. applicant_id) is missing, sets clarification_required
so the runner can return to the client for user input. Single-loan only.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from loan_agent.agent.context import AgentContext, IntentOutput

logger = logging.getLogger(__name__)

REQUIRED_ENTITIES = {
    "full_underwriting": ["applicant_id"],
    "credit_only": ["applicant_id"],
    "general_question": [],
}


def run_intent_node(ctx: AgentContext, model: str = "gpt-4.1-mini", user_request: Optional[str] = None) -> None:
    """
    Run the Intent node. Updates ctx.intent and possibly ctx.clarification_required.

    If user_request is provided (e.g. from chat reply), it is used for LLM extraction.
    Otherwise, if ctx already has entities (e.g. from API), we set intent from that.
    """
    if user_request is not None:
        ctx.user_request = user_request

    # Pre-filled entities from API (runner sets them before calling Intent)
    existing = getattr(ctx, "_prefilled_entities", None) or {}
    if existing.get("applicant_id"):
        intent_type = "full_underwriting"
        entities = {
            "applicant_id": existing.get("applicant_id"),
            "loan_id": existing.get("loan_id"),
            "months": int(existing.get("months", 6)),
        }
        ctx.intent = IntentOutput(
            intent_type=intent_type,
            entities=entities,
            needs_clarification=False,
            clarification_question=None,
        )
        ctx.append_trace("intent", {"intent_type": intent_type, "entities": entities})
        logger.info("checkpoint: intent detected (from API)", extra={"intent_type": intent_type})
        return

    # Try LLM extraction from user_request
    if ctx.user_request and ctx.user_request.strip():
        extracted = _extract_intent_llm(ctx.user_request, model)
        if extracted:
            intent_type = extracted.get("intent_type", "full_underwriting")
            entities = extracted.get("entities", {})
            required = REQUIRED_ENTITIES.get(intent_type, ["applicant_id"])
            missing = [r for r in required if not entities.get(r)]
            if missing:
                ctx.intent = IntentOutput(
                    intent_type=intent_type,
                    entities=entities,
                    needs_clarification=True,
                    clarification_question=f"Please provide: {', '.join(missing)} (e.g. applicant_id for underwriting).",
                )
                ctx.clarification_required = True
                ctx.clarification_question = ctx.intent.clarification_question
                ctx.append_trace("intent", {"intent_type": intent_type, "missing": missing})
                logger.info("checkpoint: intent needs clarification", extra={"missing": missing})
                return
            ctx.intent = IntentOutput(intent_type=intent_type, entities=entities, needs_clarification=False)
            ctx.append_trace("intent", {"intent_type": intent_type, "entities": entities})
            logger.info("checkpoint: intent detected", extra={"intent_type": intent_type})
            return

    # No request or extraction failed: ask for applicant
    ctx.intent = IntentOutput(
        intent_type="full_underwriting",
        entities={},
        needs_clarification=True,
        clarification_question="Please provide an applicant_id to run underwriting.",
    )
    ctx.clarification_required = True
    ctx.clarification_question = ctx.intent.clarification_question
    ctx.append_trace("intent", {"intent_type": "full_underwriting", "missing": ["applicant_id"]})
    logger.info("checkpoint: intent needs clarification (no applicant_id)")


def _extract_intent_llm(user_request: str, model: str) -> Optional[Dict[str, Any]]:
    """Use OpenAI to extract intent_type and entities from natural language."""
    try:
        from openai import OpenAI
    except ImportError:
        return None
    try:
        client = OpenAI()
        response = client.responses.create(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an underwriting assistant. Extract from the user message: "
                        "1) intent_type: one of full_underwriting, credit_only, general_question. "
                        "2) entities: JSON object with applicant_id (UUID if mentioned), loan_id (if any), months (number, default 6). "
                        "Reply with ONLY a JSON object: {\"intent_type\": \"...\", \"entities\": {...}}. "
                        "Do not invent IDs; use null for missing values."
                    ),
                },
                {"role": "user", "content": user_request},
            ],
        )
        text = (response.output_text or "").strip()
        if not text:
            return None
        return json.loads(text)
    except Exception:
        return None
