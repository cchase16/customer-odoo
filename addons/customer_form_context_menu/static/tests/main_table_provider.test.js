/** @odoo-module **/

import { expect, test } from "@odoo/hoot";

import {
    CUSTOM_GROUP,
    MAIN_TABLE_ITEM_ID,
    MAIN_TABLE_LABEL,
    MainTablePlaceholderDialog,
    mainTableItem,
} from "../src/providers/main_table_provider";
import { MenuItemRegistry } from "../src/registry/menu_item_registry";

test("registers the exact Main Table placeholder in the Custom group", () => {
    expect(mainTableItem.id).toBe(MAIN_TABLE_ITEM_ID);
    expect(mainTableItem.group).toBe(CUSTOM_GROUP);
    expect(mainTableItem.label).toBe("Go to the Main Table form");
    expect(MAIN_TABLE_LABEL).toBe("Go to the Main Table form");
    expect(mainTableItem.isVisible({})).toBe(true);
    expect(mainTableItem.isEnabled({})).toBe(true);
    expect(MainTablePlaceholderDialog.props.body.type).toBe(String);
});

test("executes through the dialog facade with the exact body and no navigation", () => {
    const calls = [];
    const services = {
        dialog: {
            add: (...args) => calls.push(["dialog.add", args]),
        },
        action: {
            doAction: () => calls.push(["action.doAction"]),
        },
    };

    mainTableItem.handler({}, services);

    expect(calls).toHaveLength(1);
    expect(calls[0][0]).toBe("dialog.add");
    expect(calls[0][1][0]).toBe(MainTablePlaceholderDialog);
    expect(calls[0][1][1]).toEqual({ body: "Go to the Main Table form" });
    expect(calls.some(([name]) => name.startsWith("action."))).toBe(false);
});

test("removing the provider removes only its item from a registry model", () => {
    const registry = new MenuItemRegistry();
    registry.add({
        ...mainTableItem,
        handler: mainTableItem.handler,
    });
    registry.add({
        id: "fixture.navigation",
        group: "Navigation",
        label: "Back",
        handler: () => undefined,
    });

    expect(registry.has(MAIN_TABLE_ITEM_ID)).toBe(true);
    expect(registry.remove(MAIN_TABLE_ITEM_ID)).toBe(true);
    expect(registry.has(MAIN_TABLE_ITEM_ID)).toBe(false);
    expect(registry.has("fixture.navigation")).toBe(true);
    expect(registry.buildModel()[0].items[0].id).toBe("fixture.navigation");
});

