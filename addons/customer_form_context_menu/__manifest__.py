# -*- coding: utf-8 -*-

{
    "name": "Right-click Context Menu",
    "summary": "Extensible right-click context menu",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "license": "LGPL-3",
    "author": "Chris Chase",
    "website": "https://www.odoo.com",
    "depends": ["web"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "customer_form_context_menu/static/src/registry/menu_item_registry.js",
            "customer_form_context_menu/static/src/services/context_menu_service.js",
            "customer_form_context_menu/static/src/coordinator/context_menu_coordinator.js",
            "customer_form_context_menu/static/src/services/context_menu_coordinator_service.js",
            "customer_form_context_menu/static/src/adapter/form_context_adapter.js",
            "customer_form_context_menu/static/src/components/context_menu.js",
            "customer_form_context_menu/static/src/components/context_menu.xml",
            "customer_form_context_menu/static/src/components/context_menu.scss",
            "customer_form_context_menu/static/src/components/context_menu_renderer.js",
            "customer_form_context_menu/static/src/providers/navigation_provider.js",
            "customer_form_context_menu/static/src/providers/main_table_provider.js",
            "customer_form_context_menu/static/src/bootstrap.js",
        ],
        "web.assets_unit_tests": [
            "customer_form_context_menu/static/tests/**/*",
        ],
    },
    "installable": True,
    "application": False,
}
