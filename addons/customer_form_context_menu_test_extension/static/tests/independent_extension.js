/** @odoo-module **/

import { contextMenuRegistry } from "@customer_form_context_menu/static/src/registry/menu_item_registry";

export const INDEPENDENT_EXTENSION_IDS = Object.freeze({
    visible: "fixture.extension.visible",
    hidden: "fixture.extension.hidden",
    enabled: "fixture.extension.enabled",
    disabled: "fixture.extension.disabled",
    synchronous: "fixture.extension.synchronous",
    asynchronous: "fixture.extension.asynchronous",
    existingGroup: "fixture.extension.navigation",
    namespacedGroup: "fixture.extension.namespaced",
    failure: "fixture.extension.failure",
});

function add(definition) {
    return contextMenuRegistry.add({
        group: "Independent Extension",
        groupSequence: 30,
        ...definition,
    });
}

export const independentExtensionItems = Object.freeze({
    visible: add({
        id: INDEPENDENT_EXTENSION_IDS.visible,
        sequence: 10,
        label: "Independent visible command",
        handler: () => "visible",
    }),
    hidden: add({
        id: INDEPENDENT_EXTENSION_IDS.hidden,
        sequence: 20,
        label: "Independent hidden command",
        isVisible: () => false,
        handler: () => "hidden",
    }),
    enabled: add({
        id: INDEPENDENT_EXTENSION_IDS.enabled,
        sequence: 30,
        label: "Independent enabled command",
        isEnabled: () => true,
        handler: () => "enabled",
    }),
    disabled: add({
        id: INDEPENDENT_EXTENSION_IDS.disabled,
        sequence: 40,
        label: "Independent disabled command",
        isEnabled: () => false,
        disabledReason: "Disabled by the independent fixture.",
        handler: () => "disabled",
    }),
    synchronous: add({
        id: INDEPENDENT_EXTENSION_IDS.synchronous,
        sequence: 50,
        label: "Independent synchronous command",
        handler: (_context, services) => {
            services.notification.add("Independent extension ran.");
            return "synchronous";
        },
    }),
    asynchronous: add({
        id: INDEPENDENT_EXTENSION_IDS.asynchronous,
        sequence: 60,
        label: "Independent asynchronous command",
        handler: async (_context, services) => {
            services.notification.add("Independent async extension ran.");
            return "asynchronous";
        },
    }),
    existingGroup: contextMenuRegistry.add({
        id: INDEPENDENT_EXTENSION_IDS.existingGroup,
        group: "Navigation",
        groupSequence: 10,
        sequence: 90,
        label: "Independent navigation extension",
        handler: () => "existing-group",
    }),
    namespacedGroup: contextMenuRegistry.add({
        id: INDEPENDENT_EXTENSION_IDS.namespacedGroup,
        group: "Independent Extension / Namespaced",
        groupSequence: 31,
        sequence: 10,
        label: "Independent namespaced command",
        handler: () => "namespaced-group",
    }),
    failure: add({
        id: INDEPENDENT_EXTENSION_IDS.failure,
        sequence: 70,
        label: "Independent failing command",
        handler: () => {
            throw new Error("fixture failure");
        },
    }),
});

