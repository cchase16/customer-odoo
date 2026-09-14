/** @odoo-module **/

import { registry } from "@web/core/registry";

import { renderContextMenu } from "../components/context_menu_renderer";
import { ContextMenuCoordinator } from "../coordinator/context_menu_coordinator";

export function makeContextMenuCoordinator({ env, contextMenu, options = {} }) {
    const coordinator = new ContextMenuCoordinator({
        ...options,
        serviceFacade: contextMenu,
        routeBus: options.routeBus ?? env.bus,
        renderMenu: options.renderMenu ?? ((opening) => renderContextMenu({ env, ...opening })),
    });
    coordinator.start();
    return coordinator;
}

export const contextMenuCoordinatorService = {
    dependencies: ["context_menu"],
    start(env, services) {
        return makeContextMenuCoordinator({ env, contextMenu: services.context_menu });
    },
    stop(coordinator) {
        coordinator.destroy();
    },
};

registry.category("services").add("context_menu_coordinator", contextMenuCoordinatorService);
