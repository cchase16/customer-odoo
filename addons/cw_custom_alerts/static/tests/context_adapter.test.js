/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import { buildFormContext, buildListContext, visibleFormFields } from "../src/context_adapter";

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

test("form context carries an explicit selected field without adding other fields", () => {
    expect(buildFormContext({
        resModel: "res.partner",
        actionId: 8,
        viewId: 9,
        companyId: 10,
        recordId: 11,
        visibleFields: ["email"],
        selectedFieldName: "email",
    })).toEqual({
        modelName: "res.partner",
        actionId: 8,
        viewId: 9,
        recordId: 11,
        companyId: 10,
        resolvedDomain: [],
        visibleFields: ["email"],
        selectedFieldName: "email",
    });
});

test("form field capture ignores nested subview modifiers", () => {
    const viewArch = new DOMParser().parseFromString(`
        <form>
            <field name="partner_id"/>
            <field name="state" invisible="state == 'cancel'"/>
            <field name="order_line">
                <list>
                    <field name="display_type" invisible="display_type not in ['line_section', 'line_subsection']"/>
                </list>
            </field>
            <field name="unsafe_field" invisible="missing_parent_value"/>
        </form>
    `, "text/xml").documentElement;
    const fields = visibleFormFields({
        config: { viewArch },
        model: {
            root: {
                activeFields: {
                    partner_id: {},
                    state: {},
                    order_line: {},
                    unsafe_field: {},
                },
                evalContext: { state: "cancel" },
                evalContextWithVirtualIds: { state: "draft" },
            },
        },
    });

    expect(fields).toEqual(["partner_id", "state", "order_line"]);
});
