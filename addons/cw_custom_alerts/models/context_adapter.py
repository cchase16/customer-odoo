# -*- coding: utf-8 -*-
"""Server-side validation of context captured by the Odoo web client."""

from collections.abc import Mapping

from odoo import api, models
from odoo.exceptions import AccessError, UserError

from .validation import AlertConfigurationError, canonicalize_domain


class AlertContextAdapter(models.AbstractModel):
    """Rebuild and authorize page context before it reaches the wizard."""

    _name = "alert.context.adapter"
    _description = "Custom Alert Context Adapter"

    @api.model
    def capture(self, payload):
        if not isinstance(payload, Mapping):
            raise UserError("The alert context must be a JSON object.")

        model_name = payload.get("modelName")
        if not isinstance(model_name, str) or not model_name or "." not in model_name:
            raise UserError("The alert context does not identify a valid model.")
        try:
            target_model = self.env[model_name]
        except (KeyError, ValueError) as error:
            raise UserError("The selected model is not available.") from error
        if (
            getattr(target_model, "_transient", False)
            or getattr(target_model, "_abstract", False)
            or not getattr(target_model, "_auto", True)
        ):
            raise UserError("Alerts can only be created for persistent concrete models.")
        target_model.check_access("read")

        action = self._validate_action(payload.get("actionId"), model_name)
        view = self._validate_view(payload.get("viewId"), model_name)

        try:
            domain = canonicalize_domain(payload.get("resolvedDomain") or [], target_model)
        except AlertConfigurationError as error:
            raise UserError(str(error)) from error
        if domain is None:
            domain = []
        # Search under the caller's rights so malformed or inaccessible context
        # cannot be smuggled into a rule through a later preview or activation.
        target_model.search(domain, limit=1)

        record_id = payload.get("recordId")
        if record_id in (None, False, 0):
            record_id = None
        elif not isinstance(record_id, int) or isinstance(record_id, bool) or record_id <= 0:
            raise UserError("The current record identifier is invalid.")
        else:
            record = target_model.browse(record_id).exists()
            if not record:
                raise UserError("The current record no longer exists.")
            record.check_access("read")

        visible_fields = self._eligible_visible_fields(target_model, payload.get("visibleFields"))
        return {
            "model_name": model_name,
            "action_id": action.id if action else False,
            "view_id": view.id if view else False,
            "record_id": record_id,
            "company_id": self.env.company.id,
            "resolved_domain": domain,
            "visible_fields": visible_fields,
            "scope_type": "current_record" if record_id else "captured_domain",
        }

    def _validate_action(self, action_id, model_name):
        if action_id in (None, False, 0):
            return self.env["ir.actions.act_window"]
        if not isinstance(action_id, int) or isinstance(action_id, bool) or action_id <= 0:
            raise UserError("The originating action identifier is invalid.")
        action = self.env["ir.actions.act_window"].browse(action_id).exists()
        if not action or action.res_model != model_name:
            raise UserError("The originating action does not match the selected model.")
        action.check_access("read")
        if action.group_ids and not (action.group_ids & self.env.user.all_group_ids):
            raise AccessError("You cannot use the originating action.")
        return action

    def _validate_view(self, view_id, model_name):
        if view_id in (None, False, 0):
            return self.env["ir.ui.view"]
        if not isinstance(view_id, int) or isinstance(view_id, bool) or view_id <= 0:
            raise UserError("The originating view identifier is invalid.")
        view = self.env["ir.ui.view"].browse(view_id).exists()
        if not view or view.model != model_name:
            raise UserError("The originating view does not match the selected model.")
        view.check_access("read")
        return view

    @staticmethod
    def _eligible_visible_fields(target_model, field_names):
        if not isinstance(field_names, (list, tuple)):
            raise UserError("Visible fields must be a JSON array.")
        eligible_types = {
            "boolean", "char", "text", "integer", "float", "monetary", "selection",
            "date", "datetime", "many2one",
        }
        result = []
        for field_name in field_names:
            if not isinstance(field_name, str) or field_name in result:
                continue
            field = target_model._fields.get(field_name)
            if field and getattr(field, "store", False) and field.type in eligible_types:
                result.append(field_name)
        return result
