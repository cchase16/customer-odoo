/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

import { contextMenuRegistry } from "@customer_form_context_menu/registry/menu_item_registry";
import { buildFormContext, openAlertWizard } from "./context_adapter";

export const CUSTOM_ALERT_CONTEXT_MENU_ID = "cw_custom_alerts.create";

export function buildContextMenuAlertPayload(context) {
    const selectedFieldName = context?.selectedFieldName;
    return buildFormContext({
        resModel: context?.model,
        actionId: context?.actionId,
        viewId: context?.viewId,
        companyId: user.activeCompany?.id,
        recordId: context?.recordId,
        visibleFields: selectedFieldName ? [selectedFieldName] : [],
        selectedFieldName,
    });
}

export const customAlertContextMenuItem = contextMenuRegistry.add({
    id: CUSTOM_ALERT_CONTEXT_MENU_ID,
    group: _t("Alerts"),
    groupSequence: 20,
    sequence: 10,
    label: _t("Create a custom alert"),
    isVisible: (context) => Boolean(context?.model && context?.selectedFieldName),
    isEnabled: (context) => Boolean(context?.recordId) && !context?.isNew,
    disabledReason: _t("Save the record before creating an alert."),
    handler: (context, services) =>
        openAlertWizard(services, buildContextMenuAlertPayload(context)),
});
