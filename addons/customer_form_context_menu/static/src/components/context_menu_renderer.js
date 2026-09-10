/** @odoo-module **/

import { mountComponent } from "@web/env";

import { ContextMenu } from "./context_menu";

/**
 * Adapt the coordinator's synchronous render hook to Owl's asynchronous app
 * mounting. The returned handle is usable immediately, so a close that races
 * the mount cannot leave a detached menu or an orphaned Owl app behind.
 */
export function renderContextMenu({ env, model, anchor, execute, close, focusTarget }) {
    const target = document.createElement("div");
    target.className = "o_customer_context_menu_mount";
    document.body.append(target);

    let app;
    let destroyed = false;
    mountComponent(ContextMenu, target, {
        env,
        props: {
            model,
            anchor,
            onExecute: execute,
            onClose: close,
            focusTarget,
            direction: document.documentElement.dir || "ltr",
        },
    }).then((mountedApp) => {
        app = mountedApp;
        if (destroyed) {
            app.destroy();
        }
    }).catch(() => {
        // The coordinator already owns the event decision. If Owl cannot
        // mount, remove the placeholder and leave later openings recoverable.
        destroyed = true;
        target.remove();
    });

    return {
        element: target,
        contains: (node) => target.contains(node),
        destroy() {
            if (destroyed) {
                return;
            }
            destroyed = true;
            app?.destroy();
            target.remove();
        },
    };
}
