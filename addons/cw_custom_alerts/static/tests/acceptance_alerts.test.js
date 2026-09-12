/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import { buildFormContext, buildListContext } from "../src/context_adapter";
import { normalizeInboxState } from "../src/notification_service";

test("sales-order acceptance fixture captures the filtered list boundary", () => {
    const context = buildListContext({
        resModel: "sale.order",
        actionId: 101,
        viewId: 102,
        companyId: 103,
        domain: [["state", "=", "draft"]],
        visibleFields: ["name", "partner_id", "state"],
    });
    expect(context.modelName).toBe("sale.order");
    expect(context.resolvedDomain).toEqual([["state", "=", "draft"]]);
    expect(context.recordId).toBe(null);
});

test("purchase delivery acceptance fixture captures a persisted form", () => {
    const context = buildFormContext({
        resModel: "purchase.order",
        actionId: 201,
        viewId: 202,
        companyId: 203,
        recordId: 204,
        visibleFields: ["partner_id", "date_planned"],
    });
    expect(context.modelName).toBe("purchase.order");
    expect(context.recordId).toBe(204);
    expect(context.resolvedDomain).toEqual([]);
});

test("offline and access-suppressed fixtures consume server durable state", () => {
    const serverState = normalizeInboxState({
        count: 1,
        notifications: [{
            id: 301,
            subject: "Offline alert",
            message: "Stored notification",
            severity: "info",
            action: false,
        }],
    });
    expect(serverState.count).toBe(1);
    expect(serverState.notifications[0].action).toBe(false);
});

