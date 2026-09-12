# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .validation import AlertConfigurationError, validate_rule_configuration


EVENT_TYPES = [
    ("record_created", "Record has been created"),
    ("record_deleted", "Record has been deleted"),
    ("field_changed", "Has changed"),
    ("field_becomes", "Has become"),
    ("field_is_no_longer", "Is no longer"),
    ("field_postponed", "Has been postponed"),
    ("field_advanced", "Has been advanced"),
    ("date_reached", "Date has arrived"),
    ("date_relative_before", "Before date"),
    ("date_relative_after", "After date"),
]

AUTOMATION_SYNC_FIELDS = {
    "active", "status", "model_id", "field_id", "event_type", "scope_type", "target_res_id",
    "scope_domain_json", "condition_domain_json", "date_offset_amount", "date_offset_unit",
    "date_offset_direction", "expires_at", "name",
}


class AlertRule(models.Model):
    _name = "alert.rule"
    _description = "Custom Alert Rule"
    _rec_name = "name"
    _order = "id desc"

    name = fields.Char(string="Rule Name", required=True, index=True)
    active = fields.Boolean(string="Active", default=True, index=True)
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("paused", "Paused"),
            ("expired", "Expired"),
            ("error", "Error"),
        ],
        string="Status",
        required=True,
        default="draft",
        index=True,
    )
    creator_user_id = fields.Many2one(
        "res.users",
        string="Created By",
        required=True,
        default=lambda self: self.env.user,
        index=True,
        ondelete="restrict",
    )
    recipient_user_id = fields.Many2one(
        "res.users",
        string="Recipient",
        required=True,
        default=lambda self: self.env.user,
        index=True,
        ondelete="restrict",
    )
    model_id = fields.Many2one(
        "ir.model",
        string="Watched Model",
        required=True,
        index=True,
        ondelete="cascade",
    )
    field_id = fields.Many2one(
        "ir.model.fields",
        string="Watched Field",
        index=True,
        ondelete="set null",
    )
    event_type = fields.Selection(EVENT_TYPES, string="Event", required=True, default="record_created", index=True)
    comparison_value_json = fields.Json(string="Comparison Value")
    scope_type = fields.Selection(
        [
            ("current_record", "This record only"),
            ("captured_domain", "All records matching this view"),
        ],
        string="Scope",
        required=True,
        default="current_record",
        index=True,
    )
    target_res_id = fields.Integer(string="Target Record", index=True)
    scope_domain_json = fields.Json(string="Captured Scope Domain")
    condition_domain_json = fields.Json(string="Additional Condition Domain")
    action_id = fields.Many2one("ir.actions.act_window", string="Origin Action", ondelete="set null", index=True)
    view_id = fields.Many2one("ir.ui.view", string="Origin View", ondelete="set null", index=True)
    company_ids = fields.Many2many(
        "res.company",
        "alert_rule_company_rel",
        "rule_id",
        "company_id",
        string="Companies",
        default=lambda self: self.env.company,
    )
    organization_wide = fields.Boolean(string="Organization Wide", default=False, index=True)
    date_offset_amount = fields.Integer(string="Date Offset", default=0)
    date_offset_unit = fields.Selection(
        [
            ("minutes", "Minutes"),
            ("hours", "Hours"),
            ("days", "Days"),
            ("months", "Months"),
        ],
        string="Date Offset Unit",
        default="days",
    )
    date_offset_direction = fields.Selection(
        [("before", "Before"), ("after", "After")],
        string="Date Offset Direction",
        default="after",
    )
    expires_at = fields.Datetime(string="Expires At", index=True)
    subject_template = fields.Char(string="Subject", required=True, default="Custom alert")
    message_template = fields.Text(string="Message", required=True, default="A watched event occurred.")
    severity = fields.Selection(
        [
            ("info", "Information"),
            ("success", "Success"),
            ("warning", "Warning"),
            ("danger", "Danger"),
        ],
        string="Severity",
        required=True,
        default="info",
    )
    send_email = fields.Boolean(string="Send Email", default=False)
    automation_id = fields.Many2one(
        "base.automation",
        string="Generated Automation",
        ondelete="set null",
        index=True,
        copy=False,
    )
    server_action_id = fields.Many2one(
        "ir.actions.server",
        string="Generated Server Action",
        ondelete="set null",
        index=True,
        copy=False,
    )
    last_triggered_at = fields.Datetime(string="Last Triggered At", index=True, copy=False)
    trigger_count = fields.Integer(string="Trigger Count", default=0, copy=False)
    suppressed_count = fields.Integer(string="Suppressed Count", default=0, copy=False)
    last_error_at = fields.Datetime(string="Last Error At", index=True, copy=False)
    last_error_summary = fields.Char(string="Last Error", copy=False)

    @api.model
    def _event_types(self):
        return EVENT_TYPES

    @api.model_create_multi
    def create(self, vals_list):
        vals_list = [dict(vals, creator_user_id=self.env.user.id) for vals in vals_list]
        rules = super().create(vals_list)
        active_rules = rules.filtered(lambda rule: rule.active and rule.status == "active")
        if active_rules:
            active_rules._synchronize_managed_automation()
        return rules

    def write(self, vals):
        if "creator_user_id" in vals and any(vals["creator_user_id"] != rule.creator_user_id.id for rule in self):
            raise ValidationError("The rule creator cannot be changed.")
        result = super().write(vals)
        if not self.env.context.get("skip_alert_automation_sync") and set(vals).intersection(AUTOMATION_SYNC_FIELDS):
            for rule in self:
                if rule.active and rule.status == "active":
                    try:
                        rule._synchronize_managed_automation()
                    except Exception as error:
                        # Keep the user edit and leave a safe, actionable state
                        # without copying business values into diagnostics.
                        with self.env.cr.savepoint():
                            rule.with_context(skip_alert_automation_sync=True).write({
                                "active": False,
                                "status": "error",
                                "last_error_at": fields.Datetime.now(),
                                "last_error_summary": (
                                    "Managed automation synchronization failed: %s" % type(error).__name__
                                ),
                            })
                elif rule.automation_id or rule.server_action_id:
                    self.env["alert.automation.mapper"].disable(rule)
        return result

    def _synchronize_managed_automation(self):
        for rule in self:
            self.env["alert.automation.mapper"].synchronize(rule)

    def _run_from_managed_automation(self, records, eval_context):
        self.ensure_one()
        self.env["alert.event.evaluator"].evaluate_rule(self, records, eval_context)

    @api.model
    def action_open_wizard_from_context(self, payload):
        """Create a wizard only after rebuilding the browser-supplied context."""
        captured = self.env["alert.context.adapter"].capture(payload)
        model = self.env["ir.model"]._get(captured["model_name"])
        wizard = self.env["alert.rule.wizard"].create({
            "model_id": model.id,
            "action_id": captured["action_id"],
            "view_id": captured["view_id"],
            "source_record_id": captured["record_id"] or False,
            "visible_fields_json": captured["visible_fields"],
            "scope_type": captured["scope_type"],
            "scope_domain_json": captured["resolved_domain"],
            "company_id": captured["company_id"],
            "recipient_user_id": self.env.user.id,
        })
        return {
            "type": "ir.actions.act_window",
            "name": "Create a custom alert",
            "res_model": "alert.rule.wizard",
            "view_mode": "form",
            "views": [(self.env.ref("cw_custom_alerts.view_alert_rule_wizard_form").id, "form")],
            "res_id": wizard.id,
            "target": "new",
        }

    def action_activate(self):
        self.write({"active": True, "status": "active"})
        return True

    def action_pause(self):
        self.write({"active": False, "status": "paused"})
        return True

    def action_archive(self):
        self.write({"active": False, "status": "paused"})
        return True

    def action_recapture(self):
        """Explicitly revalidate the saved source context and keep it immutable otherwise."""
        for rule in self:
            if rule.scope_type != "captured_domain":
                continue
            payload = {
                "modelName": rule.model_id.model,
                "actionId": rule.action_id.id or None,
                "viewId": rule.view_id.id or None,
                "recordId": None,
                "companyId": self.env.company.id,
                "resolvedDomain": rule.scope_domain_json or [],
                "visibleFields": [],
            }
            captured = self.env["alert.context.adapter"].capture(payload)
            rule.write({"scope_domain_json": captured["resolved_domain"]})
        return True

    @api.model
    def _expire_overdue_rules(self):
        overdue = self.sudo().search([
            ("active", "=", True),
            ("status", "=", "active"),
            ("expires_at", "!=", False),
            ("expires_at", "<=", fields.Datetime.now()),
        ])
        if overdue:
            overdue.write({"active": False, "status": "expired"})
        return len(overdue)

    @api.constrains("creator_user_id", "recipient_user_id", "organization_wide", "company_ids")
    def _check_security_policy(self):
        manager = self.env.user.has_group("cw_custom_alerts.group_alert_manager")
        for rule in self:
            if not rule.recipient_user_id or rule.recipient_user_id.share:
                raise ValidationError("Alert recipients must be internal users.")
            if not rule.company_ids:
                raise ValidationError("An alert rule must include at least one company.")
            if rule.company_ids - self.env.companies:
                raise ValidationError("Alert rules cannot include companies outside the user's allowed scope.")
            if not manager:
                if rule.creator_user_id != self.env.user or rule.recipient_user_id != self.env.user:
                    raise ValidationError("Alert Users can manage only their own rules and recipients.")
                if rule.organization_wide:
                    raise ValidationError("Organization-wide alerts require Alert Manager permission.")
                if rule.company_ids != self.env.company:
                    raise ValidationError("Alert Users can scope rules only to their current company.")

    @api.constrains(
        "model_id", "field_id", "event_type", "comparison_value_json", "scope_type", "target_res_id",
        "scope_domain_json", "condition_domain_json", "date_offset_amount", "date_offset_unit",
        "date_offset_direction", "expires_at", "subject_template", "message_template", "active", "status",
    )
    def _check_configuration(self):
        for rule in self:
            if not rule.model_id:
                continue
            try:
                target_model = self.env[rule.model_id.model]
                if rule.field_id.id and rule.field_id.model_id != rule.model_id:
                    raise AlertConfigurationError("The watched field must belong to the selected model.")
                validate_rule_configuration(
                    rule._configuration_values(),
                    target_model=target_model,
                    watched_field=rule.field_id if rule.field_id.id else None,
                    at_activation=rule.active and rule.status == "active",
                )
            except (AlertConfigurationError, KeyError, ValueError) as error:
                raise ValidationError(str(error)) from error

    def _configuration_values(self):
        self.ensure_one()
        return {
            "field_id": self.field_id.id,
            "event_type": self.event_type,
            "comparison_value_json": None if self.comparison_value_json is False else self.comparison_value_json,
            "scope_type": self.scope_type,
            "target_res_id": self.target_res_id,
            "scope_domain_json": None if self.scope_domain_json is False else self.scope_domain_json,
            "condition_domain_json": None if self.condition_domain_json is False else self.condition_domain_json,
            "date_offset_amount": self.date_offset_amount,
            "date_offset_unit": self.date_offset_unit,
            "date_offset_direction": self.date_offset_direction,
            "expires_at": self.expires_at,
            "subject_template": self.subject_template,
            "message_template": self.message_template,
        }
