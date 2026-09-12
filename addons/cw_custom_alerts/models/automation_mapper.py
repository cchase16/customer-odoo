"""Odoo 19 adapter for managed alert automations."""

from __future__ import annotations

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


TIME_EVENTS = {"date_reached", "date_relative_before", "date_relative_after"}
FIELD_EVENTS = {"field_changed", "field_becomes", "field_is_no_longer", "field_postponed", "field_advanced"}
TRIGGER_BY_EVENT = {
    "record_created": "on_create",
    "record_deleted": "on_unlink",
    **{event: "on_create_or_write" for event in FIELD_EVENTS},
    **{event: "on_time" for event in TIME_EVENTS},
}
ODOO_RANGE_TYPES = {"minutes": "minutes", "hours": "hour", "days": "day", "months": "month"}


class AlertAutomationMapper(models.AbstractModel):
    _name = "alert.automation.mapper"
    _description = "Custom Alert Automation Mapper"

    @api.model
    def _domain_for_rule(self, rule):
        if rule.scope_type != "captured_domain":
            return False
        domain = []
        if rule.scope_domain_json:
            domain.extend(rule.scope_domain_json)
        if rule.condition_domain_json:
            domain.extend(rule.condition_domain_json)
        return repr(domain) if domain else False

    @api.model
    def _prepare_automation_values(self, rule, *, active, previous=None):
        trigger = TRIGGER_BY_EVENT.get(rule.event_type)
        if not trigger:
            raise ValidationError(_("Unsupported event type for automation mapping."))
        values = {
            "name": _("CW Alert: %s", rule.name),
            "model_id": rule.model_id.id,
            "trigger": trigger,
            "filter_domain": self._domain_for_rule(rule),
            "active": active,
            "alert_rule_id": rule.id,
        }
        if trigger == "on_create_or_write" and rule.field_id:
            values["trigger_field_ids"] = [(6, 0, [rule.field_id.id])]
        if trigger == "on_time":
            if not rule.field_id or rule.field_id.ttype not in {"date", "datetime"}:
                raise ValidationError(_("Time-based alert rules require a date or datetime field."))
            values.update({
                "trg_date_id": rule.field_id.id,
                "trg_date_range": rule.date_offset_amount,
                "trg_date_range_mode": rule.date_offset_direction,
                "trg_date_range_type": ODOO_RANGE_TYPES[rule.date_offset_unit],
            })
            if not previous or previous.trigger != "on_time":
                values["last_run"] = fields.Datetime.now()
        return values

    @api.model
    def _prepare_action_values(self, rule, automation, *, active):
        return {
            "name": _("CW Alert Dispatch: %s", rule.name),
            "model_id": rule.model_id.id,
            "usage": "base_automation",
            "base_automation_id": automation.id,
            "alert_rule_id": rule.id,
            "state": "cw_alert_dispatch",
            "code": False,
        }

    @api.model
    def synchronize(self, rule):
        """Create or update exactly one action and automation atomically."""
        Automation = self.env["base.automation"].with_context(active_test=False).sudo()
        Action = self.env["ir.actions.server"].with_context(active_test=False).sudo()
        with self.env.cr.savepoint():
            automation = Automation.search([("alert_rule_id", "=", rule.id)], order="id", limit=1)
            previous = automation
            if not automation:
                automation = Automation.create(self._prepare_automation_values(rule, active=True))
            else:
                automation.write(self._prepare_automation_values(rule, active=True, previous=previous))

            actions = Action.search([("alert_rule_id", "=", rule.id)], order="id")
            action = actions[:1]
            if not action:
                action = Action.create(self._prepare_action_values(rule, automation, active=True))
            else:
                action.write(self._prepare_action_values(rule, automation, active=True))
            if automation.trigger == "on_create_or_write" and rule.field_id:
                automation.write({"trigger_field_ids": [(4, rule.field_id.id)]})
            automation.write({"action_server_ids": [(6, 0, [action.id])]})

            # A duplicate is a configuration defect; remove only managed duplicates.
            duplicate_actions = actions - action
            if duplicate_actions:
                duplicate_actions.unlink()
            duplicate_automations = Automation.search([("alert_rule_id", "=", rule.id), ("id", "!=", automation.id)])
            if duplicate_automations:
                duplicate_automations.write({"action_server_ids": [(5, 0, 0)]})
                duplicate_automations.unlink()
            rule.sudo().with_context(skip_alert_automation_sync=True).write({
                "automation_id": automation.id,
                "server_action_id": action.id,
            })
        return automation, action

    @api.model
    def disable(self, rule):
        for automation in rule.automation_id.sudo():
            automation.write({"active": False})
        return True


class BaseAutomation(models.Model):
    _inherit = "base.automation"

    alert_rule_id = fields.Many2one(
        "alert.rule", string="Managed Alert Rule", index=True, ondelete="cascade", copy=False,
    )

    def _cron_process_time_based_actions(self):
        try:
            return super()._cron_process_time_based_actions()
        finally:
            self.env["alert.rule"].sudo()._expire_overdue_rules()

    def _process(self, records, domain_post=None):
        """Preserve old ORM values for the trusted alert runner.

        Odoo's stock processor intentionally passes only active-record context
        to server actions. Alert comparison needs the automation's old-value
        snapshot, so this narrow adapter mirrors that processor while adding a
        namespaced, non-executable context value.
        """
        if not self.filtered("alert_rule_id"):
            return super()._process(records, domain_post=domain_post)
        automation_done = self.env.context.get("__action_done", {})
        records_done = automation_done.get(self, records.browse())
        records -= records_done
        if not records:
            return
        if self.env.context.get("__action_feedback"):
            automation_done[self] = records_done + records
        else:
            automation_done = dict(automation_done)
            automation_done[self] = records_done + records
            self = self.with_context(__action_done=automation_done)
            records = records.with_context(__action_done=automation_done)
        records = records.filtered(self._check_trigger_fields)
        automation_done[self] = records_done + records
        if records and "date_automation_last" in records._fields:
            records.date_automation_last = self.env.cr.now()
        old_values = self.env.context.get("old_values")
        contexts = [
            {
                "active_model": record._name,
                "active_ids": record.ids,
                "active_id": record.id,
                "domain_post": domain_post,
                "cw_alert_old_values": old_values,
            }
            for record in records
        ]
        for action in self.sudo().action_server_ids:
            for ctx in contexts:
                try:
                    action.with_context(**ctx).run()
                except Exception as error:
                    self._add_postmortem(error)
                    raise


class IrActionsServer(models.Model):
    _inherit = "ir.actions.server"

    state = fields.Selection(
        selection_add=[("cw_alert_dispatch", "Custom Alert Dispatch")],
        ondelete={"cw_alert_dispatch": "cascade"},
    )
    alert_rule_id = fields.Many2one(
        "alert.rule", string="Managed Alert Rule", index=True, ondelete="cascade", copy=False,
    )

    def _run_action_cw_alert_dispatch_multi(self, eval_context=None):
        self.ensure_one()
        if not self.alert_rule_id or not self.alert_rule_id.active or self.alert_rule_id.status != "active":
            return False
        records = (eval_context or {}).get("records")
        if records is None:
            records = self.env[self.model_id.model].browse(self.env.context.get("active_ids", []))
        context = dict(eval_context or {})
        context["old_values"] = self.env.context.get("cw_alert_old_values")
        self.alert_rule_id.sudo()._run_from_managed_automation(records, context)
        return False
