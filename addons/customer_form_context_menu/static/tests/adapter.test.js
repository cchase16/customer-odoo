/** @odoo-module **/

import { afterEach, expect, test } from "@odoo/hoot";

import {
    FORM_ADAPTER_VERSION,
    FormContextAdapter,
    fieldNameFromTarget,
} from "../src/adapter/form_context_adapter";
import { ContextMenuCoordinator } from "../src/coordinator/context_menu_coordinator";
import { MenuItemRegistry } from "../src/registry/menu_item_registry";

const activeCoordinators = [];
const createdRoots = [];

afterEach(() => {
    for (const coordinator of activeCoordinators.splice(0)) {
        coordinator.destroy();
    }
    for (const root of createdRoots.splice(0)) {
        root.remove();
    }
});

function makeController(root, { inDialog = false, resId = 20, resIds = [10, 20, 30] } = {}) {
    const calls = [];
    const record = {
        resModel: "res.partner",
        resId,
        resIds,
        isNew: resId === false,
        dirty: false,
    };
    const controller = {
        rootRef: { el: root },
        env: { inDialog, config: { actionId: 41, viewId: 42 } },
        model: {
            root: record,
            load: (...args) => calls.push(["load", args]),
        },
        actionService: {
            restore: (...args) => calls.push(["restore", args]),
        },
        beforeLeave: () => {
            calls.push(["beforeLeave"]);
            return true;
        },
        onPagerUpdate: (...args) => calls.push(["pager", args]),
        calls,
    };
    return controller;
}

function makeRoot() {
    const root = document.createElement("form");
    const button = document.createElement("button");
    const fieldWidget = document.createElement("div");
    fieldWidget.className = "o_field_widget";
    fieldWidget.setAttribute("name", "email");
    const fieldInput = document.createElement("input");
    fieldWidget.append(fieldInput);
    root.append(button, fieldWidget);
    document.body.append(root);
    createdRoots.push(root);
    return { root, button, fieldInput, fieldWidget };
}

function makeAdapter(controller, coordinator) {
    return new FormContextAdapter({ controller, coordinator });
}

test("registers main, dialog, embedded, and nested form roots with the coordinator", () => {
    const main = makeRoot();
    const nested = makeRoot();
    main.root.append(nested.root);
    const dialog = makeRoot();
    const registry = new MenuItemRegistry();
    registry.add({ id: "fixture.command", group: "Fixture", label: "Command", handler: () => {} });
    const coordinator = new ContextMenuCoordinator({
        menuRegistry: registry,
        serviceFacade: { notification: { add: () => {} } },
        renderMenu: () => ({ destroy: () => {} }),
    });
    activeCoordinators.push(coordinator);
    const mainAdapter = makeAdapter(makeController(main.root), coordinator);
    const nestedAdapter = makeAdapter(makeController(nested.root), coordinator);
    const dialogAdapter = makeAdapter(makeController(dialog.root, { inDialog: true }), coordinator);
    mainAdapter.mount();
    nestedAdapter.mount();
    dialogAdapter.mount();
    coordinator.start();

    const nestedEvent = new MouseEvent("contextmenu", { bubbles: true, cancelable: true });
    nested.button.dispatchEvent(nestedEvent);
    expect(nestedEvent.defaultPrevented).toBe(true);
    expect(coordinator.openMenu.context.surface).toBe("main");
    expect(coordinator.openMenu.context.recordId).toBe(20);
    coordinator.close();

    const dialogEvent = new MouseEvent("contextmenu", { bubbles: true, cancelable: true });
    dialog.button.dispatchEvent(dialogEvent);
    expect(dialogEvent.defaultPrevented).toBe(true);
    expect(coordinator.openMenu.context.surface).toBe("dialog");
    expect(coordinator.openMenu.context.inDialog).toBe(true);
});

test("captures the field under the context-menu pointer", () => {
    const fixture = makeRoot();
    const registry = new MenuItemRegistry();
    registry.add({ id: "fixture.command", label: "Command", handler: () => {} });
    const coordinator = new ContextMenuCoordinator({
        menuRegistry: registry,
        serviceFacade: { notification: { add: () => {} } },
        renderMenu: () => ({ destroy: () => {} }),
    });
    activeCoordinators.push(coordinator);
    makeAdapter(makeController(fixture.root), coordinator).mount();
    coordinator.start();

    fixture.fieldInput.dispatchEvent(
        new MouseEvent("contextmenu", { bubbles: true, cancelable: true })
    );

    expect(coordinator.openMenu.context.selectedFieldName).toBe("email");
    expect(coordinator.openMenu.context.actionId).toBe(41);
    expect(coordinator.openMenu.context.viewId).toBe(42);
});

test("creates a short-lived snapshot without exposing controller or model objects", () => {
    const { root, fieldInput } = makeRoot();
    const controller = makeController(root, { resId: 20, resIds: [10, 20, 30] });
    const coordinator = { registerForm: () => () => {} };
    const adapter = makeAdapter(controller, coordinator);
    const snapshot = adapter.createContextSnapshot(
        Object.freeze({ clientX: 5, clientY: 6 }),
        fieldInput
    );

    expect(snapshot.adapterVersion).toBe(FORM_ADAPTER_VERSION);
    expect(snapshot.surface).toBe("main");
    expect(snapshot.model).toBe("res.partner");
    expect(snapshot.recordIds).toEqual([10, 20, 30]);
    expect(snapshot.pager.offset).toBe(1);
    expect(snapshot.pager.canPrevious).toBe(true);
    expect(snapshot.pager.canNext).toBe(true);
    expect(snapshot.anchor.clientX).toBe(5);
    expect(snapshot.actionId).toBe(41);
    expect(snapshot.viewId).toBe(42);
    expect(snapshot.selectedFieldName).toBe("email");
    expect(snapshot.controller).toBe(undefined);
    expect(snapshot.modelObject).toBe(undefined);
    expect(Object.isFrozen(snapshot)).toBe(true);
    expect(Object.isFrozen(snapshot.recordIds)).toBe(true);
});

test("field selection accepts only a named widget inside the registered form", () => {
    const { root, button, fieldInput } = makeRoot();
    const outside = document.createElement("div");
    outside.className = "o_field_widget";
    outside.setAttribute("name", "phone");
    document.body.append(outside);

    expect(fieldNameFromTarget(root, fieldInput)).toBe("email");
    expect(fieldNameFromTarget(root, button)).toBe(null);
    expect(fieldNameFromTarget(root, outside)).toBe(null);
    outside.remove();
});

test("exposes guarded navigation operations without leaking controller internals", async () => {
    const { root } = makeRoot();
    const controller = makeController(root);
    const adapter = makeAdapter(controller, { registerForm: () => () => {} });
    const navigation = adapter.getNavigationFacade();

    expect(navigation.state().canPrevious).toBe(true);
    await navigation.previous();
    await navigation.next();
    await navigation.back();
    await navigation.refresh();
    expect(controller.calls.map(([name]) => name)).toEqual([
        "pager",
        "pager",
        "beforeLeave",
        "restore",
        "beforeLeave",
        "load",
    ]);
    expect(navigation.controller).toBe(undefined);

    const callCountBeforeBlockedNavigation = controller.calls.length;
    controller.beforeLeave = () => false;
    expect(await navigation.back()).toBe(false);
    expect(await navigation.refresh()).toBe(false);
    expect(controller.calls.length).toBe(callCountBeforeBlockedNavigation);
});

test("does not offer pager operations for a new record", () => {
    const { root } = makeRoot();
    const controller = makeController(root, { resId: false, resIds: [] });
    const adapter = makeAdapter(controller, { registerForm: () => () => {} });
    const navigation = adapter.getNavigationFacade();

    expect(navigation.state().canPrevious).toBe(false);
    expect(navigation.state().canNext).toBe(false);
    expect(navigation.previous()).toBe(false);
    expect(navigation.next()).toBe(false);
    expect(controller.calls).toEqual([]);
});

test("leaves native context menus intact when adapter initialization fails", () => {
    const { root, button } = makeRoot();
    const controller = makeController(root);
    controller.rootRef.el = null;
    const registrations = [];
    const coordinator = {
        registerForm: (...args) => {
            registrations.push(args);
            return () => {};
        },
    };
    const adapter = makeAdapter(controller, coordinator);
    expect(() => adapter.mount()).toThrow(Error);
    expect(registrations).toHaveLength(0);
    expect(adapter.active).toBe(true);
    expect(button.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true }))).toBe(true);
});

test("unregisters the exact root and closes stale ownership on unmount", () => {
    const { root } = makeRoot();
    let unregisterCalls = 0;
    const coordinator = {
        registerForm: () => () => {
            unregisterCalls += 1;
        },
    };
    const adapter = makeAdapter(makeController(root), coordinator);
    adapter.mount();
    adapter.mount();
    adapter.unmount();
    adapter.unmount();
    expect(unregisterCalls).toBe(1);
    expect(adapter.active).toBe(false);
    expect(adapter.controller).toBe(null);
});
