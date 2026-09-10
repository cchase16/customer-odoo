# -*- coding: utf-8 -*-

{
    "name": "Customer Form Context Menu Test Extension",
    "summary": "Test-only independent context-menu registry contribution",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "license": "LGPL-3",
    "author": "Customer Odoo",
    "depends": ["customer_form_context_menu"],
    "data": [],
    "assets": {
        "web.assets_unit_tests": [
            "customer_form_context_menu_test_extension/static/tests/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
