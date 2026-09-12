/** @odoo-module */

/**
 * JSON-safe fields the Odoo 19 context adapter may hand to the server.
 * Controller, model, recordset, and service objects are deliberately absent.
 */
export const CONTEXT_TRANSFER_FIELDS = Object.freeze([
    "modelName",
    "actionId",
    "viewId",
    "recordId",
    "companyId",
    "resolvedDomain",
    "visibleFields",
]);

const CONTEXT_TRANSFER_FIELD_SET = new Set(CONTEXT_TRANSFER_FIELDS);

export function isContextTransfer(value) {
    return Boolean(
        value &&
            typeof value === "object" &&
            Object.keys(value).every((fieldName) => CONTEXT_TRANSFER_FIELD_SET.has(fieldName)) &&
            typeof value.modelName === "string" &&
            Array.isArray(value.visibleFields) &&
            value.visibleFields.every((fieldName) => typeof fieldName === "string")
    );
}
