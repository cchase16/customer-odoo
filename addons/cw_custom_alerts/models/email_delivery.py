# -*- coding: utf-8 -*-

import html
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AlertEmailDelivery(models.AbstractModel):
    _name = "alert.email.delivery"
    _description = "Custom Alert Email Delivery"

    def queue(self, notifications):
        """Queue fixed-format mail from already rendered plain text."""
        Mail = self.env["mail.mail"].sudo()
        for notification in notifications:
            partner = notification.user_id.partner_id
            if not partner.email:
                notification.sudo().write({
                    "email_state": "failed",
                    "email_error_summary": "Recipient has no email address",
                })
                continue
            body = html.escape(notification.message or "").replace("\n", "<br/>\n")
            try:
                with self.env.cr.savepoint():
                    Mail.create({
                        "subject": notification.subject or "Custom alert",
                        "body_html": (
                            "<div class=\"o_cw_custom_alert_email\">"
                            "<p>%s</p></div>" % body
                        ),
                        "email_to": partner.email,
                        "auto_delete": False,
                        "alert_notification_id": notification.id,
                    })
            except Exception as error:  # keep inbox delivery independent
                notification.sudo().write({
                    "email_state": "failed",
                    "email_error_summary": "Email queue failed: %s" % type(error).__name__,
                })
                _logger.warning("Custom alert email queue failed: %s", type(error).__name__)
            else:
                notification.sudo().write({"email_state": "queued", "email_error_summary": False})


class AlertMailMail(models.Model):
    _inherit = "mail.mail"

    alert_notification_id = fields.Many2one(
        "alert.notification", string="Custom Alert", index=True, copy=False, ondelete="set null"
    )

    def _postprocess_sent_message(self, success_pids, success_emails, failure_reason=False, failure_type=None):
        result = super()._postprocess_sent_message(
            success_pids, success_emails, failure_reason=failure_reason, failure_type=failure_type
        )
        linked = self.filtered("alert_notification_id")
        if linked:
            if failure_reason:
                linked.mapped("alert_notification_id").sudo().write({
                    "email_state": "failed",
                    "email_error_summary": "Email delivery failed",
                })
            else:
                linked.mapped("alert_notification_id").sudo().write({
                    "email_state": "sent",
                    "email_sent_at": fields.Datetime.now(),
                    "email_error_summary": False,
                })
        return result
