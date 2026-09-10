/** @odoo-module **/

import { onMounted, onWillUnmount } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { FormController } from "@web/views/form/form_controller";

export const FORM_ADAPTER_VERSION = "odoo-19";

function copyRecordIds(root) {
    if (Array.isArray(root.resIds)) {
        return [...root.resIds];
    }
    return root.resId ? [root.resId] : [];
}

/**
 * The only module allowed to access release-sensitive FormController APIs.
 * It converts a controller into a small registration and navigation facade;
 * controller and model objects never enter the context snapshot.
 */
export class FormContextAdapter {
    constructor({ controller, coordinator }) {
        if (!controller || !coordinator) {
            throw new TypeError("FormContextAdapter requires a controller and coordinator");
        }
        this.controller = controller;
        this.coordinator = coordinator;
        this.unregister = null;
        this.active = true;
    }

    mount() {
        if (this.unregister) {
            return this.unregister;
        }
        const root = this.controller.rootRef?.el;
        if (!root) {
            throw new Error("The Odoo form root is not available for context-menu registration");
        }
        this.unregister = this.coordinator.registerForm(root, ({ anchor }) =>
            this.createContextSnapshot(anchor)
        );
        return this.unregister;
    }

    unmount() {
        this.active = false;
        if (this.unregister) {
            this.unregister();
            this.unregister = null;
        }
        this.controller = null;
    }

    getNavigationState() {
        const root = this.controller?.model?.root;
        if (!root) {
            return Object.freeze({
                isNew: true,
                offset: -1,
                total: 0,
                canPrevious: false,
                canNext: false,
            });
        }
        const recordIds = copyRecordIds(root);
        const isNew = Boolean(root.isNew);
        const offset = isNew ? -1 : recordIds.indexOf(root.resId);
        return Object.freeze({
            isNew,
            offset,
            total: recordIds.length,
            canPrevious: !isNew && offset > 0,
            canNext: !isNew && offset >= 0 && offset < recordIds.length - 1,
        });
    }

    createContextSnapshot(anchor) {
        if (!this.active || !this.controller) {
            throw new Error("The form context adapter is no longer active");
        }
        const { controller } = this;
        const root = controller.model?.root;
        if (!root) {
            throw new Error("The Odoo form model is not ready for context-menu registration");
        }
        const recordIds = copyRecordIds(root);
        const navigation = this.getNavigationState();
        return Object.freeze({
            adapterVersion: FORM_ADAPTER_VERSION,
            surface: controller.env?.inDialog ? "dialog" : "main",
            inDialog: Boolean(controller.env?.inDialog),
            model: root.resModel ?? null,
            recordId: root.resId || false,
            recordIds: Object.freeze(recordIds),
            isNew: Boolean(root.isNew),
            // FormController exposes `dirty` synchronously. Do not call the
            // async isDirty() method while opening or evaluating predicates.
            dirty: Boolean(root.dirty),
            pager: navigation,
            anchor,
            navigation: this.getNavigationFacade(),
        });
    }

    async withDirtyGuard(operation) {
        if (!this.active || !this.controller) {
            return false;
        }
        const canLeave = await this.controller.beforeLeave({});
        if (canLeave === false) {
            return false;
        }
        return operation();
    }

    getNavigationFacade() {
        return Object.freeze({
            state: () => this.getNavigationState(),
            back: () =>
                this.withDirtyGuard(() => {
                    if (!this.controller?.actionService?.restore) {
                        return false;
                    }
                    return this.controller.actionService.restore();
                }),
            previous: () => {
                const state = this.getNavigationState();
                if (!state.canPrevious || !this.controller?.onPagerUpdate) {
                    return false;
                }
                return this.controller.onPagerUpdate({
                    offset: state.offset - 1,
                    resIds: copyRecordIds(this.controller.model.root),
                });
            },
            next: () => {
                const state = this.getNavigationState();
                if (!state.canNext || !this.controller?.onPagerUpdate) {
                    return false;
                }
                return this.controller.onPagerUpdate({
                    offset: state.offset + 1,
                    resIds: copyRecordIds(this.controller.model.root),
                });
            },
            refresh: () =>
                this.withDirtyGuard(() =>
                    this.controller?.model?.load ? this.controller.model.load() : false
                ),
        });
    }
}

/** Install the adapter from FormController.setup without exposing internals. */
export function useFormContextAdapter(controller) {
    const coordinator = useService("context_menu_coordinator");
    const adapter = new FormContextAdapter({ controller, coordinator });
    onMounted(() => {
        try {
            adapter.mount();
        } catch (error) {
            // An unavailable root/model means the coordinator has no owner;
            // its fail-safe therefore leaves the native browser menu intact.
            coordinator.routeError?.(error, "adapter", undefined);
        }
    });
    onWillUnmount(() => adapter.unmount());
    return adapter;
}

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);
        this.customerFormContextMenuAdapter = useFormContextAdapter(this);
    },
});
