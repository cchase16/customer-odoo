/** @odoo-module **/

import { registry } from "@web/core/registry";

import { contextMenuRegistry } from "../registry/menu_item_registry";

const serviceRegistry = registry.category("services");

/**
 * Construct the stable command facade exposed to menu handlers.
 * Only documented methods are forwarded; raw Odoo services are not returned.
 */
export function makeContextMenuService({
    action,
    dialog,
    notification,
    orm,
    menuRegistry = contextMenuRegistry,
}) {
    return Object.freeze({
        getItems(context = {}) {
            return menuRegistry.buildModel(context);
        },
        action: Object.freeze({
            doAction: (...args) => action.doAction(...args),
            doActionButton: (...args) => action.doActionButton(...args),
            switchView: (...args) => action.switchView(...args),
            restore: (...args) => action.restore(...args),
        }),
        dialog: Object.freeze({
            add: (...args) => dialog.add(...args),
            closeAll: (...args) => dialog.closeAll(...args),
        }),
        notification: Object.freeze({
            add: (...args) => notification.add(...args),
        }),
        orm: Object.freeze({
            call: (...args) => orm.call(...args),
        }),
    });
}

export const contextMenuService = {
    dependencies: ["action", "dialog", "notification", "orm"],
    start(_env, services) {
        return makeContextMenuService(services);
    },
};

serviceRegistry.add("context_menu", contextMenuService);
