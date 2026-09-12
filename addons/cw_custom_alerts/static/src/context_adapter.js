/** @odoo-module */

import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component } from "@odoo/owl";

function jsonCopy(value) {
    return JSON.parse(JSON.stringify(value ?? null));
}

export function buildListContext({ resModel, actionId, viewId, companyId, domain, visibleFields }) {
    return {
        modelName: resModel,
        actionId: actionId || null,
        viewId: viewId || null,
        recordId: null,
        companyId: companyId || null,
        resolvedDomain: jsonCopy(domain || []),
        visibleFields: [...new Set(visibleFields || [])],
    };
}

export function buildFormContext({ resModel, actionId, viewId, companyId, recordId, visibleFields }) {
    return {
        modelName: resModel,
        actionId: actionId || null,
        viewId: viewId || null,
        recordId: recordId || null,
        companyId: companyId || null,
        resolvedDomain: [],
        visibleFields: [...new Set(visibleFields || [])],
    };
}

async function openWizard(env, payload) {
    const action = await env.services.orm.call("alert.rule", "action_open_wizard_from_context", [payload]);
    return env.services.action.doAction(action);
}

function visibleListFields(env) {
    return (env.model.root.activeFields ? Object.keys(env.model.root.activeFields) : []).filter(
        (fieldName) => typeof fieldName === "string"
    );
}

function visibleFormFields(env) {
    const nodes = env.config.viewArch?.querySelectorAll?.("field") || [];
    const evalContext = env.model.root.evalContext || {};
    return [...nodes]
        .filter((node) => !node.getAttribute("invisible") || !evaluateBooleanExpr(node.getAttribute("invisible"), evalContext))
        .map((node) => node.getAttribute("name"))
        .filter(Boolean);
}

export class CustomAlertCogMenu extends Component {
    static template = "cw_custom_alerts.CustomAlertCogMenu";
    static components = { DropdownItem };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async createCustomAlert() {
        const root = this.env.model?.root;
        if (!root || !root.resModel) {
            return;
        }
        const common = {
            resModel: root.resModel,
            actionId: this.env.config.actionId,
            viewId: this.env.config.viewId,
            companyId: user.activeCompany?.id,
        };
        const payload = this.env.config.viewType === "form"
            ? buildFormContext({ ...common, recordId: root.isNew ? null : root.resId, visibleFields: visibleFormFields(this.env) })
            : buildListContext({ ...common, domain: this.env.searchModel?.domain || [], visibleFields: visibleListFields(this.env) });
        return openWizard(this.env, payload);
    }
}

export const customAlertCogMenuItem = {
    Component: CustomAlertCogMenu,
    groupNumber: 1,
    isDisplayed: async (env) =>
        ["list", "form"].includes(env.config.viewType) &&
        Boolean(env.model?.root?.resModel) &&
        (env.config.viewType !== "form" || !env.model.root.isNew),
};

registry.category("cogMenu").add("cw_custom_alerts.create", customAlertCogMenuItem, { sequence: 25 });
