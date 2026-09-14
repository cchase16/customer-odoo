/** @odoo-module */

import { expect, test } from "@odoo/hoot";

import {
    buildContextMenuAlertPayload,
    customAlertContextMenuItem,
} from "../src/context_menu_provider";

function persistedFieldContext() {
    return {
        model: "res.partner",
        recordId: 17,
        isNew: false,
        actionId: 23,
        viewId: 29,
        selectedFieldName: "email",
    };
}

test("right-click alert item is scoped to a selected field on a saved form", () => {
    const context = persistedFieldContext();
    expect(customAlertContextMenuItem.isVisible(context)).toBe(true);
    expect(customAlertContextMenuItem.isEnabled(context)).toBe(true);
    expect(customAlertContextMenuItem.isVisible({ ...context, selectedFieldName: null })).toBe(false);
    expect(customAlertContextMenuItem.isEnabled({ ...context, recordId: false, isNew: true })).toBe(false);

    const payload = buildContextMenuAlertPayload(context);
    expect(payload.modelName).toBe("res.partner");
    expect(payload.recordId).toBe(17);
    expect(payload.actionId).toBe(23);
    expect(payload.viewId).toBe(29);
    expect(payload.visibleFields).toEqual(["email"]);
    expect(payload.selectedFieldName).toBe("email");
});

test("right-click alert handler opens the same server-backed wizard as the cog action", async () => {
    const calls = [];
    const returnedAction = { type: "ir.actions.act_window", res_model: "alert.rule.wizard" };
    const services = {
        orm: {
            call: async (...args) => {
                calls.push(["orm", args]);
                return returnedAction;
            },
        },
        action: {
            doAction: (...args) => {
                calls.push(["action", args]);
                return "opened";
            },
        },
    };

    expect(await customAlertContextMenuItem.handler(persistedFieldContext(), services)).toBe("opened");
    expect(calls[0][0]).toBe("orm");
    expect(calls[0][1][0]).toBe("alert.rule");
    expect(calls[0][1][1]).toBe("action_open_wizard_from_context");
    expect(calls[0][1][2][0].visibleFields).toEqual(["email"]);
    expect(calls[1]).toEqual(["action", [returnedAction]]);
});
