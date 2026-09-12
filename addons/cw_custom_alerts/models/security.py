# -*- coding: utf-8 -*-
"""Access checks used before exposing recipient-facing record details."""

from dataclasses import dataclass

from odoo.exceptions import AccessError, MissingError


@dataclass(frozen=True)
class AccessDecision:
    """Minimal decision object; it intentionally carries no business values."""

    allowed: bool
    reason: str


def recipient_can_read(env, recipient, model_name, res_id, company=None):
    """Check model and record access in the recipient's company context.

    Failure reasons are operational labels only. Callers must not render a
    record name, field value, subject, or message before this returns allowed.
    """
    if not recipient or not model_name or not isinstance(res_id, int) or res_id <= 0:
        return AccessDecision(False, "invalid_reference")
    context = dict(env.context)
    if company:
        context["allowed_company_ids"] = [company.id]
    try:
        recipient_env = env(user=recipient, context=context, su=False)
        model = recipient_env[model_name]
        model.check_access("read")
        record = model.browse(res_id)
        if not record.exists():
            return AccessDecision(False, "record_missing")
        record.check_access("read")
    except (AccessError, MissingError, KeyError, ValueError):
        return AccessDecision(False, "access_denied")
    return AccessDecision(True, "allowed")
