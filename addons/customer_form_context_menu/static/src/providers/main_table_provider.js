/** @odoo-module **/

import { Component, xml } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

import { contextMenuRegistry } from "../registry/menu_item_registry";

export const MAIN_TABLE_ITEM_ID = "customer_form_context_menu.custom.main_table";
export const MAIN_TABLE_LABEL = _t("Go to the Main Table form");
export const CUSTOM_GROUP = "Custom";
export const CUSTOM_GROUP_SEQUENCE = 20;

/**
 * Temporary Main Table surface. The provider owns this placeholder so a
 * future navigation implementation can replace one callback without
 * changing the framework, registry, or navigation providers.
 */
export class MainTablePlaceholderDialog extends Component {
    static components = { Dialog };
    static props = {
        body: { type: String },
        close: { type: Function },
    };
    static template = xml`
        <Dialog header="false" size="'sm'">
            <p class="text-prewrap"><t t-esc="props.body"/></p>
            <t t-set-slot="footer">
                <button type="button" class="btn btn-primary" t-on-click="props.close">
                    <t t-esc="closeLabel"/>
                </button>
            </t>
        </Dialog>
    `;

    get closeLabel() {
        return _t("Close");
    }
}

export const mainTableItem = contextMenuRegistry.add({
    id: MAIN_TABLE_ITEM_ID,
    group: CUSTOM_GROUP,
    groupSequence: CUSTOM_GROUP_SEQUENCE,
    sequence: 10,
    label: MAIN_TABLE_LABEL,
    isVisible: () => true,
    isEnabled: () => true,
    handler: (_context, services) =>
        services.dialog.add(MainTablePlaceholderDialog, {
            body: String(MAIN_TABLE_LABEL),
        }),
});

