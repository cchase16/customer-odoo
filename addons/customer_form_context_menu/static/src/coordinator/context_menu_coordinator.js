/** @odoo-module **/

import { EventBus } from "@odoo/owl";

import { contextMenuRegistry } from "../registry/menu_item_registry";

export const CONTEXT_MENU_EVENTS = Object.freeze({
    OPEN: "OPEN",
    CLOSE: "CLOSE",
    ERROR: "ERROR",
});

export const CLOSE_REASONS = Object.freeze({
    REPLACE: "replace",
    ESCAPE: "escape",
    OUTSIDE: "outside",
    ROUTE_CHANGE: "route-change",
    FORM_DESTROYED: "form-destroyed",
    RESIZE: "resize",
    SCROLL: "scroll",
    EXECUTE: "execute",
    NATIVE_BYPASS: "native-bypass",
    DESTROY: "destroy",
});

function defaultErrorHandler(_error, { phase }) {
    // Do not log the error object: provider errors can accidentally contain
    // record values. The event still gives the host a safe place to observe it.
    console.error(`[customer_form_context_menu] ${phase} failed`);
}

function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isValidModel(model) {
    return (
        Array.isArray(model) &&
        model.length > 0 &&
        model.every(
            (group) =>
                isObject(group) &&
                typeof group.id === "string" &&
                Array.isArray(group.items) &&
                group.items.length > 0 &&
                group.items.every(
                    (item) =>
                        isObject(item) &&
                        typeof item.id === "string" &&
                        typeof item.label === "string" &&
                        typeof item.disabled === "boolean" &&
                        typeof item.handler === "function"
                )
        )
    );
}

function makeAnchor(event) {
    return Object.freeze({
        clientX: Number.isFinite(event.clientX) ? event.clientX : 0,
        clientY: Number.isFinite(event.clientY) ? event.clientY : 0,
    });
}

function makeKeyboardAnchor(event) {
    const target = event.target;
    const rect = target?.getBoundingClientRect?.() ?? { left: 0, right: 0, bottom: 0 };
    const direction = target?.closest?.("[dir]")?.dir || globalThis.document?.documentElement?.dir;
    return Object.freeze({
        clientX: Number(direction === "rtl" ? rect.right ?? rect.left : rect.left) || 0,
        clientY: Number(rect.bottom) || 0,
    });
}

function makeSnapshot(value, anchor) {
    if (!isObject(value)) {
        throw new TypeError("A form context factory must return an object snapshot");
    }
    return Object.freeze({ ...value, anchor });
}

/**
 * Owns context-menu event handling and command execution, without knowing
 * about the form controller or the menu component implementation.
 *
 * A registered form supplies a short-lived snapshot factory. A renderer can
 * be supplied by the Owl component phase; it receives an immutable opening
 * record and may return { element, destroy }. The coordinator remains usable
 * without a renderer so unit tests and host integrations can subscribe to
 * OPEN/CLOSE events.
 */
export class ContextMenuCoordinator extends EventBus {
    constructor({
        menuRegistry = contextMenuRegistry,
        serviceFacade,
        renderMenu = null,
        documentRef = globalThis.document,
        windowRef = globalThis.window,
        routeBus = null,
        errorHandler = defaultErrorHandler,
    } = {}) {
        super();
        if (!serviceFacade || typeof serviceFacade !== "object") {
            throw new TypeError("ContextMenuCoordinator requires the context-menu service facade");
        }
        this.menuRegistry = menuRegistry;
        this.serviceFacade = serviceFacade;
        this.renderMenu = renderMenu;
        this.documentRef = documentRef;
        this.windowRef = windowRef;
        this.routeBus = routeBus;
        this.errorHandler = errorHandler;
        this.registrations = [];
        this.openMenu = null;
        this.started = false;
        this._nextRegistrationId = 1;
        this._nextMenuId = 1;
        this._boundContextMenu = (event) => this.handleContextMenu(event);
        this._boundPointerDown = (event) => this.handlePointerDown(event);
        this._boundClick = (event) => this.handlePointerDown(event);
        this._boundKeyDown = (event) => this.handleKeyDown(event);
        this._boundResize = () => this.close(CLOSE_REASONS.RESIZE);
        this._boundScroll = () => this.close(CLOSE_REASONS.SCROLL);
        this._boundRouteChange = () => this.closeForRouteChange();
    }

    start() {
        if (this.started) {
            return this;
        }
        this.started = true;
        this.documentRef?.addEventListener("contextmenu", this._boundContextMenu, true);
        this.documentRef?.addEventListener("pointerdown", this._boundPointerDown, true);
        this.documentRef?.addEventListener("click", this._boundClick, true);
        this.documentRef?.addEventListener("keydown", this._boundKeyDown, true);
        this.windowRef?.addEventListener("resize", this._boundResize);
        this.windowRef?.addEventListener("scroll", this._boundScroll, true);
        if (this.routeBus?.addEventListener) {
            this.routeBus.addEventListener("ROUTE_CHANGE", this._boundRouteChange);
        } else if (this.routeBus?.on) {
            this.routeBus.on("ROUTE_CHANGE", this, this._boundRouteChange);
        }
        return this;
    }

    stop() {
        if (!this.started) {
            return;
        }
        this.close(CLOSE_REASONS.DESTROY);
        this.documentRef?.removeEventListener("contextmenu", this._boundContextMenu, true);
        this.documentRef?.removeEventListener("pointerdown", this._boundPointerDown, true);
        this.documentRef?.removeEventListener("click", this._boundClick, true);
        this.documentRef?.removeEventListener("keydown", this._boundKeyDown, true);
        this.windowRef?.removeEventListener("resize", this._boundResize);
        this.windowRef?.removeEventListener("scroll", this._boundScroll, true);
        if (this.routeBus?.removeEventListener) {
            this.routeBus.removeEventListener("ROUTE_CHANGE", this._boundRouteChange);
        } else if (this.routeBus?.off) {
            this.routeBus.off("ROUTE_CHANGE", this, this._boundRouteChange);
        }
        this.registrations = [];
        this.started = false;
    }

    destroy() {
        this.stop();
    }

    /** Register a form root and return an idempotent unregister function. */
    registerForm(root, makeContext) {
        if (!root || typeof makeContext !== "function") {
            throw new TypeError("A form registration requires a root and context factory");
        }
        const registration = {
            id: this._nextRegistrationId++,
            root,
            makeContext,
        };
        this.registrations.push(registration);
        return () => this.unregisterForm(registration);
    }

    unregisterForm(registrationOrRoot) {
        const index = this.registrations.findIndex(
            (registration) =>
                registration === registrationOrRoot || registration.root === registrationOrRoot
        );
        if (index < 0) {
            return false;
        }
        const [registration] = this.registrations.splice(index, 1);
        if (this.openMenu?.registration === registration) {
            this.close(CLOSE_REASONS.FORM_DESTROYED);
        }
        return true;
    }

    findRegistration(event) {
        const path = event.composedPath?.() ?? [];
        for (const node of path) {
            const registration = this.registrations.find(({ root }) => root === node);
            if (registration) {
                return registration;
            }
        }
        let node = event.target;
        while (node) {
            const registration = this.registrations.find(({ root }) => root === node);
            if (registration) {
                return registration;
            }
            node = node.parentElement;
        }
        return null;
    }

    handleContextMenu(event, { allowNativeBypass = event.type === "contextmenu" } = {}) {
        if (!this.started || event.defaultPrevented) {
            return false;
        }
        if (allowNativeBypass && event.shiftKey) {
            // Shift + right-click is the explicit escape hatch to the browser's
            // native editing, spelling, extension, and developer menu.
            this.close(CLOSE_REASONS.NATIVE_BYPASS, { restoreFocus: false });
            return false;
        }
        const registration = this.findRegistration(event);
        if (!registration) {
            return false;
        }

        const anchor = makeAnchor(event);
        let context;
        let model;
        try {
            context = makeSnapshot(registration.makeContext({ event, anchor }), anchor);
            model = this.menuRegistry.buildModel(context);
            if (!isValidModel(model)) {
                return false;
            }
        } catch (error) {
            this.routeError(error, "model", undefined);
            return false;
        }

        if (this.openMenu) {
            this.close(CLOSE_REASONS.REPLACE, { restoreFocus: false });
        }
        const opening = {
            id: this._nextMenuId++,
            registration,
            root: registration.root,
            model,
            context,
            anchor,
            focusTarget: this.documentRef?.activeElement ?? null,
            executed: new Set(),
            renderHandle: null,
        };
        this.openMenu = opening;
        try {
            if (this.renderMenu) {
                opening.renderHandle = this.renderMenu({
                    ...opening,
                    execute: (itemOrId) => this.execute(itemOrId),
                    close: (reason) => this.close(reason),
                });
            }
        } catch (error) {
            this.close("render-error", { restoreFocus: false });
            this.routeError(error, "render", undefined);
            return false;
        }

        // The native menu is suppressed only after the form produced a
        // non-empty valid model and the host accepted the opening request.
        event.preventDefault();
        this.trigger(CONTEXT_MENU_EVENTS.OPEN, opening);
        return true;
    }

    handlePointerDown(event) {
        const open = this.openMenu;
        if (!open) {
            return false;
        }
        if (open.renderHandle?.contains?.(event.target)) {
            return false;
        }
        return this.close(CLOSE_REASONS.OUTSIDE);
    }

    handleKeyDown(event) {
        if (event.key === "ContextMenu" || (event.key === "F10" && event.shiftKey)) {
            if (this.openMenu) {
                return false;
            }
            const registration = this.findRegistration(event);
            if (!registration) {
                return false;
            }
            const anchor = makeKeyboardAnchor(event);
            const keyboardEvent = {
                ...event,
                target: event.target,
                key: event.key,
                shiftKey: event.shiftKey,
                clientX: anchor.clientX,
                clientY: anchor.clientY,
                composedPath: () => event.composedPath?.() ?? [],
                defaultPrevented: false,
                preventDefault: () => {
                    event.preventDefault();
                    keyboardEvent.defaultPrevented = true;
                },
            };
            // Shift+F10 is an accessibility shortcut for this custom menu, not
            // the pointer-only Shift + right-click native-menu bypass.
            const handled = this.handleContextMenu(keyboardEvent, {
                allowNativeBypass: false,
            });
            if (handled) {
                event.stopPropagation();
            }
            return handled;
        }
        if (!this.openMenu || event.key !== "Escape") {
            return false;
        }
        event.preventDefault();
        event.stopPropagation();
        return this.close(CLOSE_REASONS.ESCAPE);
    }

    closeForRouteChange() {
        return this.close(CLOSE_REASONS.ROUTE_CHANGE);
    }

    close(reason = "manual", { restoreFocus = true } = {}) {
        const opening = this.openMenu;
        if (!opening) {
            return false;
        }
        this.openMenu = null;
        try {
            opening.renderHandle?.destroy?.();
        } catch (error) {
            this.routeError(error, "cleanup", undefined);
        }
        this.trigger(CONTEXT_MENU_EVENTS.CLOSE, { opening, reason });
        if (restoreFocus) {
            this.restoreFocus(opening.focusTarget);
        }
        return true;
    }

    restoreFocus(target) {
        if (target && target.isConnected !== false && typeof target.focus === "function") {
            target.focus({ preventScroll: true });
        }
    }

    execute(itemOrId) {
        const opening = this.openMenu;
        const itemId = typeof itemOrId === "string" ? itemOrId : itemOrId?.id;
        const item = opening?.model
            .flatMap((group) => group.items)
            .find((candidate) => candidate.id === itemId);
        if (!opening || !item || item.disabled || opening.executed.has(item.id)) {
            return false;
        }
        opening.executed.add(item.id);
        const context = opening.context;
        this.close(CLOSE_REASONS.EXECUTE);
        let result;
        try {
            result = item.handler(context, this.serviceFacade);
        } catch (error) {
            this.routeError(error, "handler", item.id);
            return false;
        }
        if (result && typeof result.then === "function") {
            return Promise.resolve(result).catch((error) => {
                this.routeError(error, "handler", item.id);
                return undefined;
            });
        }
        return result;
    }

    routeError(error, phase, itemId) {
        const details = Object.freeze({ phase, itemId });
        try {
            this.serviceFacade.notification?.add(
                "The context-menu command could not be completed.",
                { type: "danger" }
            );
        } catch {
            // Notification failures must not obscure the original error.
        }
        try {
            this.errorHandler(error, details);
        } catch {
            // Error reporting must not break event ownership or later opens.
        }
        this.trigger(CONTEXT_MENU_EVENTS.ERROR, details);
    }
}
