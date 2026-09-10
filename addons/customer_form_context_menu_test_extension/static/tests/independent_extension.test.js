/** @odoo-module **/

import { expect, test } from "@odoo/hoot";

import { ContextMenuCoordinator } from "@customer_form_context_menu/static/src/coordinator/context_menu_coordinator";
import {
    contextMenuRegistry,
    MenuItemRegistry,
} from "@customer_form_context_menu/static/src/registry/menu_item_registry";

import {
    INDEPENDENT_EXTENSION_IDS,
    independentExtensionItems,
} from "./independent_extension";

function modelFromFixture(context = {}) {
    const model = contextMenuRegistry.buildModel(context);
    return model.filter((group) =>
        group.items.some((item) => item.id.startsWith("fixture.extension."))
    );
}

test("loads independently and contributes conditional, grouped commands", () => {
    const model = modelFromFixture();
    const independentGroup = model.find((group) => group.id === "Independent Extension");
    const navigationGroup = model.find((group) => group.id === "Navigation");
    const namespacedGroup = model.find(
        (group) => group.id === "Independent Extension / Namespaced"
    );

    expect(independentGroup.items.map((item) => item.id)).toEqual([
        INDEPENDENT_EXTENSION_IDS.visible,
        INDEPENDENT_EXTENSION_IDS.enabled,
        INDEPENDENT_EXTENSION_IDS.disabled,
        INDEPENDENT_EXTENSION_IDS.synchronous,
        INDEPENDENT_EXTENSION_IDS.asynchronous,
        INDEPENDENT_EXTENSION_IDS.failure,
    ]);
    expect(
        independentGroup.items.find((item) => item.id === INDEPENDENT_EXTENSION_IDS.disabled).disabled
    ).toBe(true);
    expect(
        independentGroup.items.some((item) => item.id === INDEPENDENT_EXTENSION_IDS.hidden)
    ).toBe(false);
    expect(
        navigationGroup.items.some((item) => item.id === INDEPENDENT_EXTENSION_IDS.existingGroup)
    ).toBe(true);
    expect(namespacedGroup.items.map((item) => item.id)).toEqual([
        INDEPENDENT_EXTENSION_IDS.namespacedGroup,
    ]);
});

test("executes synchronous and asynchronous items through the constrained facade", async () => {
    const notifications = [];
    const facade = {
        notification: { add: (message) => notifications.push(message) },
    };
    const syncItem = contextMenuRegistry.get(INDEPENDENT_EXTENSION_IDS.synchronous);
    const asyncItem = contextMenuRegistry.get(INDEPENDENT_EXTENSION_IDS.asynchronous);

    expect(syncItem.handler({}, facade)).toBe("synchronous");
    await expect(asyncItem.handler({}, facade)).resolves.toBe("asynchronous");
    expect(notifications).toEqual([
        "Independent extension ran.",
        "Independent async extension ran.",
    ]);
});

test("isolates a failing extension item and keeps later openings usable", () => {
    const root = document.createElement("form");
    const button = document.createElement("button");
    root.append(button);
    document.body.append(root);
    const errors = [];
    const coordinator = new ContextMenuCoordinator({
        menuRegistry: new MenuItemRegistry(),
        serviceFacade: { notification: { add: () => undefined } },
        errorHandler: (_error, details) => errors.push(details),
        renderMenu: () => ({
            contains: () => false,
            destroy: () => undefined,
        }),
    });
    coordinator.menuRegistry.add(contextMenuRegistry.get(INDEPENDENT_EXTENSION_IDS.failure));
    coordinator.menuRegistry.add(contextMenuRegistry.get(INDEPENDENT_EXTENSION_IDS.visible));
    coordinator.registerForm(root, () => ({}));
    coordinator.start();

    button.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true }));
    expect(coordinator.execute(INDEPENDENT_EXTENSION_IDS.failure)).toBe(false);
    expect(errors).toEqual([{ phase: "handler", itemId: INDEPENDENT_EXTENSION_IDS.failure }]);

    button.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true }));
    expect(Boolean(coordinator.openMenu)).toBe(true);
    coordinator.destroy();
    root.remove();
});

test("removing the independent fixture needs no framework change", () => {
    expect(Object.keys(independentExtensionItems)).toEqual([
        "visible",
        "hidden",
        "enabled",
        "disabled",
        "synchronous",
        "asynchronous",
        "existingGroup",
        "namespacedGroup",
        "failure",
    ]);
    expect(contextMenuRegistry.has(INDEPENDENT_EXTENSION_IDS.visible)).toBe(true);
});

