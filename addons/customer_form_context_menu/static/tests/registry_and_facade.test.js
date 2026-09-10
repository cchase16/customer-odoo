/** @odoo-module **/

import { expect, test } from "@odoo/hoot";

import {
    DEFAULT_GROUP,
    DEFAULT_GROUP_SEQUENCE,
    DEFAULT_SEQUENCE,
    DuplicateMenuItemError,
    MenuItemContractError,
    MenuItemRegistry,
    ReservedMenuItemError,
    contextMenuRegistry,
} from "../src/registry/menu_item_registry";
import { makeContextMenuService } from "../src/services/context_menu_service";

function definition(overrides = {}) {
    return {
        id: "fixture.item",
        group: "Fixture",
        label: "Fixture item",
        handler: () => "handled",
        ...overrides,
    };
}

test("normalizes defaults and returns immutable definitions", () => {
    const menu = new MenuItemRegistry();
    const item = menu.add(definition());

    expect(item.group).toBe("Fixture");
    expect(item.sequence).toBe(DEFAULT_SEQUENCE);
    expect(item.groupSequence).toBe(DEFAULT_GROUP_SEQUENCE);
    expect(item.isVisible({})).toBe(true);
    expect(item.isEnabled({})).toBe(true);
    expect(Object.isFrozen(item)).toBe(true);
});

test("applies the default group when it is omitted", () => {
    const menu = new MenuItemRegistry();
    menu.add(definition({ id: "fixture.default-group", group: undefined }));

    expect(menu.get("fixture.default-group").group).toBe(DEFAULT_GROUP);
});

test("orders groups, then items by sequence and identifier", () => {
    const menu = new MenuItemRegistry();
    menu.add(definition({ id: "fixture.z", group: "Beta", groupSequence: 20, sequence: 1 }));
    menu.add(definition({ id: "fixture.b", group: "Alpha", groupSequence: 10, sequence: 50 }));
    menu.add(definition({ id: "fixture.a", group: "Alpha", groupSequence: 10, sequence: 50 }));
    menu.add(definition({ id: "fixture.a-first", group: "Alpha", groupSequence: 10, sequence: 1 }));

    const model = menu.buildModel();
    expect(model.map((group) => group.id)).toEqual(["Alpha", "Beta"]);
    expect(model[0].items.map((item) => item.id)).toEqual([
        "fixture.a-first",
        "fixture.a",
        "fixture.b",
    ]);
});

test("omits hidden items and empty groups while preserving disabled items", () => {
    const menu = new MenuItemRegistry();
    menu.add(definition({ id: "fixture.hidden", group: "Hidden", isVisible: () => false }));
    menu.add(
        definition({
            id: "fixture.disabled",
            group: "Visible",
            isEnabled: () => false,
            disabledReason: "Not available in this context",
        })
    );

    const model = menu.buildModel();
    expect(model.map((group) => group.id)).toEqual(["Visible"]);
    expect(model[0].items[0].disabled).toBe(true);
    expect(model[0].items[0].disabledReason).toBe("Not available in this context");
});

test("rejects duplicate and reserved identifiers", () => {
    const menu = new MenuItemRegistry();
    menu.add(definition({ id: "fixture.duplicate" }));

    expect(() => menu.add(definition({ id: "fixture.duplicate" }))).toThrow(DuplicateMenuItemError);
    expect(() => menu.add(definition({ id: "__separator__" }))).toThrow(ReservedMenuItemError);
});

test("validates definitions and rejects asynchronous predicates", () => {
    const menu = new MenuItemRegistry();

    expect(() => menu.add(definition({ label: "" }))).toThrow(MenuItemContractError);
    expect(() => menu.add(definition({ handler: "not-a-function" }))).toThrow(MenuItemContractError);
    expect(() => menu.add(definition({ isVisible: "not-a-function" }))).toThrow(MenuItemContractError);

    menu.add(definition({ id: "fixture.async", isVisible: async () => true }));
    expect(() => menu.buildModel()).toThrow(MenuItemContractError);
});

test("reflects late registrations in the next model without stale cache", () => {
    const menu = new MenuItemRegistry();
    expect(menu.buildModel()).toEqual([]);
    menu.add(definition({ id: "fixture.late" }));

    expect(menu.buildModel()[0].items[0].id).toBe("fixture.late");
});

test("the facade exposes only the constrained service operations", () => {
    const calls = [];
    const menu = new MenuItemRegistry();
    menu.add(definition({ id: "fixture.facade" }));
    const facade = makeContextMenuService({
        menuRegistry: menu,
        action: {
            doAction: (...args) => calls.push(["doAction", args]),
            doActionButton: (...args) => calls.push(["doActionButton", args]),
            switchView: (...args) => calls.push(["switchView", args]),
            restore: (...args) => calls.push(["restore", args]),
            privateMethod: () => calls.push(["private", []]),
        },
        dialog: {
            add: (...args) => calls.push(["dialog.add", args]),
            closeAll: (...args) => calls.push(["dialog.closeAll", args]),
        },
        notification: { add: (...args) => calls.push(["notification.add", args]) },
        orm: { call: (...args) => calls.push(["orm.call", args]), read: () => {} },
    });

    facade.action.doAction("fixture-action");
    facade.dialog.add("fixture-dialog");
    facade.notification.add("fixture-notification");
    facade.orm.call("fixture.model", "fixture_method");
    expect(facade.getItems()[0].items[0].id).toBe("fixture.facade");
    expect(Object.keys(facade.action)).toEqual(["doAction", "doActionButton", "switchView", "restore"]);
    expect(Object.keys(facade.dialog)).toEqual(["add", "closeAll"]);
    expect(Object.keys(facade.orm)).toEqual(["call"]);
    expect(calls.map(([name]) => name)).toEqual([
        "doAction",
        "dialog.add",
        "notification.add",
        "orm.call",
    ]);
});

test("publishes one public registry instance for independent add-ons", () => {
    expect(Boolean(contextMenuRegistry)).toBe(true);
    expect(contextMenuRegistry).toBe(contextMenuRegistry);
});
