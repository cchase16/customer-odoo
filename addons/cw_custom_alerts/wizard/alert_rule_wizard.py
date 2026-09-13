# -*- coding: utf-8 -*-

import ast

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..models.validation import AlertConfigurationError, combine_domains, validate_rule_configuration


class AlertRuleWizard(models.TransientModel):
    _name = "alert.rule.wizard"
    _description = "Create Custom Alert"

    name = fields.Char(string="Rule Name", required=True, default=lambda self: _("New custom alert"))
    model_id = fields.Many2one("ir.model", string="Watched Model", required=True, readonly=True)
    model_name = fields.Char(related="model_id.model", string="Technical Model", readonly=True)
    action_id = fields.Many2one("ir.actions.act_window", string="Origin Action", readonly=True)
    view_id = fields.Many2one("ir.ui.view", string="Origin View", readonly=True)
    source_record_id = fields.Integer(string="Source Record", readonly=True)
    visible_fields_json = fields.Json(string="Eligible Visible Fields", readonly=True)
    scope_type = fields.Selection(
        [("current_record", "This record only"), ("captured_domain", "All records matching this view")],
        required=True,
        default="current_record",
    )
    scope_domain_json = fields.Json(string="Captured Scope Domain", readonly=True)
    condition_domain_json = fields.Json(string="Additional Conditions")
    condition_domain_input = fields.Text(string="Additional Conditions", default="[]")
    event_type = fields.Selection("_event_types", string="Event", required=True, default="record_created")
    field_id = fields.Many2one("ir.model.fields", string="Watched Field")
    comparison_value_json = fields.Json(string="Comparison Value")
    date_offset_amount = fields.Integer(string="Date Offset", default=0)
    date_offset_unit = fields.Selection(
        [("minutes", "Minutes"), ("hours", "Hours"), ("days", "Days"), ("months", "Months")],
        default="days",
    )
    date_offset_direction = fields.Selection([("before", "Before"), ("after", "After")], default="after")
    expires_at = fields.Datetime(string="Expires At")
    subject_template = fields.Char(string="Subject", required=True, default="Custom alert")
    message_template = fields.Text(string="Message", required=True, default="A watched event occurred.")
    recipient_user_id = fields.Many2one("res.users", string="Recipient", required=True, default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", string="Company", required=True, default=lambda self: self.env.company, readonly=True)
    organization_wide = fields.Boolean(string="Organization Wide")
    send_email = fields.Boolean(string="Send Email")
    preview_count = fields.Integer(string="Matching Records", readonly=True)
    review_text = fields.Text(string="Review", readonly=True)
    step = fields.Selection([("configure", "Configure"), ("review", "Review")], default="configure", required=True)

    @api.model
    def _event_types(self):
        return self.env["alert.rule"]._event_types()

    def _context_payload(self):
        self.ensure_one()
        return {
            "modelName": self.model_id.model,
            "actionId": self.action_id.id or None,
            "viewId": self.view_id.id or None,
            "recordId": self.source_record_id or None,
            "companyId": self.company_id.id,
            "resolvedDomain": self.scope_domain_json or [],
            "visibleFields": self.visible_fields_json or [],
        }

    def _capture_context(self):
        self.ensure_one()
        return self.env["alert.context.adapter"].capture(self._context_payload())

    def _configuration_values(self):
        self.ensure_one()
        condition_domain = self.condition_domain_json if self.condition_domain_json not in (False, None) else None
        if self.condition_domain_input and self.condition_domain_input.strip() not in ("", "[]"):
            try:
                condition_domain = self._literal_domain(self.condition_domain_input)
            except (SyntaxError, ValueError) as error:
                raise ValidationError("Additional conditions must be a valid domain.") from error
        return {
            "field_id": self.field_id.id if self.field_id else None,
            "event_type": self.event_type,
            "comparison_value_json": self.comparison_value_json if self.comparison_value_json not in (False, None) else None,
            "scope_type": self.scope_type,
            "target_res_id": self.source_record_id or None,
            "scope_domain_json": self.scope_domain_json if self.scope_domain_json not in (False, None) else None,
            "condition_domain_json": condition_domain,
            "date_offset_amount": self.date_offset_amount,
            "date_offset_unit": self.date_offset_unit,
            "date_offset_direction": self.date_offset_direction,
            "expires_at": self.expires_at,
            "subject_template": self.subject_template,
            "message_template": self.message_template,
        }

    def _validate(self, at_activation=False):
        self.ensure_one()
        try:
            captured = self._capture_context()
        except UserError as error:
            raise ValidationError(str(error)) from error
        model = self.env[self.model_id.model]
        field = self.field_id
        if field and field.model_id != self.model_id:
            raise ValidationError("The watched field must belong to the selected model.")
        try:
            canonical = validate_rule_configuration(
                self._configuration_values(),
                target_model=model,
                watched_field=field if field else None,
                at_activation=at_activation,
            )
        except (AlertConfigurationError, KeyError, ValueError) as error:
            raise ValidationError(str(error)) from error
        return captured, canonical

    @staticmethod
    def _literal_domain(value):
        """Convert the standard domain widget's literal text to JSON lists."""
        parsed = ast.literal_eval(value)
        if not isinstance(parsed, (list, tuple)):
            raise ValueError("not a domain")

        def as_json(item):
            if isinstance(item, (list, tuple)):
                return [as_json(value) for value in item]
            if item is None or isinstance(item, (bool, int, float, str)):
                return item
            raise ValueError("unsafe domain value")

        return as_json(parsed)

    def _effective_domain(self, model):
        self.ensure_one()
        try:
            scope_domain = self.scope_domain_json if self.scope_domain_json not in (False, None) else None
            condition_domain = self.condition_domain_json if self.condition_domain_json not in (False, None) else None
            return combine_domains(scope_domain, condition_domain, target_model=model)
        except AlertConfigurationError as error:
            raise ValidationError(str(error)) from error

    def action_preview(self):
        for wizard in self:
            captured, canonical = wizard._validate()
            wizard.write({
                "scope_domain_json": canonical["scope_domain_json"] or captured["resolved_domain"],
                "condition_domain_json": canonical["condition_domain_json"],
                "condition_domain_input": repr(canonical["condition_domain_json"] or []),
                "preview_count": self.env[wizard.model_id.model].search_count(
                    wizard._effective_domain(self.env[wizard.model_id.model])
                ),
            })
        return {"type": "ir.actions.act_window", "res_model": self._name, "res_id": self.id, "view_mode": "form", "target": "new"}

    def action_review(self):
        for wizard in self:
            wizard._validate()
            wizard.review_text = _(
                "Alert %(name)s will watch %(model)s for %(event)s and notify %(recipient)s.",
                name=wizard.name,
                model=wizard.model_id.display_name,
                event=dict(wizard._event_types()).get(wizard.event_type, wizard.event_type),
                recipient=wizard.recipient_user_id.display_name,
            )
            wizard.step = "review"
        return {"type": "ir.actions.act_window", "res_model": self._name, "res_id": self.id, "view_mode": "form", "target": "new"}

    def action_back_to_configuration(self):
        self.write({"step": "configure"})
        return {"type": "ir.actions.act_window", "res_model": self._name, "res_id": self.id, "view_mode": "form", "target": "new"}

    def action_activate(self):
        for wizard in self:
            captured, canonical = wizard._validate(at_activation=True)
            if wizard.recipient_user_id.share:
                raise ValidationError("Alert recipients must be internal users.")
            if wizard.organization_wide and not self.env.user.has_group("cw_custom_alerts.group_alert_manager"):
                raise ValidationError("Organization-wide alerts require Alert Manager permission.")
            vals = {
                "name": wizard.name,
                "model_id": wizard.model_id.id,
                "field_id": wizard.field_id.id or False,
                "event_type": wizard.event_type,
                "comparison_value_json": wizard.comparison_value_json,
                "scope_type": wizard.scope_type,
                "target_res_id": captured["record_id"] or False,
                "scope_domain_json": canonical["scope_domain_json"],
                "condition_domain_json": canonical["condition_domain_json"],
                "action_id": wizard.action_id.id or False,
                "view_id": wizard.view_id.id or False,
                "company_ids": [(6, 0, [captured["company_id"]])],
                "organization_wide": wizard.organization_wide,
                "expires_at": wizard.expires_at or False,
                "subject_template": wizard.subject_template,
                "message_template": wizard.message_template,
                "recipient_user_id": wizard.recipient_user_id.id,
                "send_email": wizard.send_email,
                "active": True,
                "status": "active",
            }
            self.env["alert.rule"].create(vals)
        return {"type": "ir.actions.act_window_close"}
