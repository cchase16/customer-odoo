# -*- coding: utf-8 -*-

{
    "name": "Custom Alerts",
    "summary": "Reusable personal alert rules and notifications",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "license": "LGPL-3",
    "author": "Customer Odoo",
    "website": "https://www.odoo.com",
    "depends": ["base_automation", "web", "bus", "mail", "customer_form_context_menu"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/alert_cron.xml",
        "views/alert_rule_views.xml",
        "views/alert_rule_wizard_views.xml",
        "views/alert_notification_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "cw_custom_alerts/static/src/alerts_bootstrap.js",
            "cw_custom_alerts/static/src/context_adapter.js",
            "cw_custom_alerts/static/src/context_menu_provider.js",
            "cw_custom_alerts/static/src/context_adapter.xml",
            "cw_custom_alerts/static/src/notification_service.js",
            "cw_custom_alerts/static/src/notification_systray.js",
            "cw_custom_alerts/static/src/notification_service.xml",
        ],
        "web.assets_unit_tests": [
            "cw_custom_alerts/static/src/contracts.js",
            "cw_custom_alerts/static/src/context_adapter.js",
            "cw_custom_alerts/static/src/context_menu_provider.js",
            "cw_custom_alerts/static/src/notification_service.js",
            "cw_custom_alerts/static/tests/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
