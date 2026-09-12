/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import { CONTEXT_TRANSFER_FIELDS, isContextTransfer } from "../src/contracts";

test("context transfer exposes only JSON-safe boundary fields", () => {
    expect(CONTEXT_TRANSFER_FIELDS).toEqual([
        "modelName",
        "actionId",
        "viewId",
        "recordId",
        "companyId",
        "resolvedDomain",
        "visibleFields",
    ]);
    expect(
        isContextTransfer({
            modelName: "res.partner",
            actionId: 1,
            viewId: 2,
            recordId: null,
            companyId: 1,
            resolvedDomain: [],
            visibleFields: ["name"],
        })
    ).toBe(true);
    expect(isContextTransfer({ modelName: "res.partner", visibleFields: ["name", 1] })).toBe(false);
    expect(isContextTransfer({ modelName: "res.partner", visibleFields: [], controller: {} })).toBe(false);
});
