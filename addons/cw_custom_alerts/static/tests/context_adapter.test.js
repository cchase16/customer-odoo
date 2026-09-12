/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import { buildFormContext, buildListContext } from "../src/context_adapter";

test("list context keeps a JSON-safe resolved domain and unique visible fields", () => {
    const domain = [["state", "=", "sale"]];
    const context = buildListContext({
        resModel: "sale.order",
        actionId: 4,
        viewId: 5,
        companyId: 6,
        domain,
        visibleFields: ["name", "name", "amount_total"],
    });
    expect(context).toEqual({
        modelName: "sale.order",
        actionId: 4,
        viewId: 5,
        recordId: null,
        companyId: 6,
        resolvedDomain: domain,
        visibleFields: ["name", "amount_total"],
    });
    expect(context.resolvedDomain).not.toBe(domain);
});

test("form context carries only a persisted record identifier", () => {
    expect(buildFormContext({
        resModel: "purchase.order",
        actionId: 8,
        viewId: 9,
        companyId: 10,
        recordId: 11,
        visibleFields: ["partner_id"],
    })).toEqual({
        modelName: "purchase.order",
        actionId: 8,
        viewId: 9,
        recordId: 11,
        companyId: 10,
        resolvedDomain: [],
        visibleFields: ["partner_id"],
    });
});
