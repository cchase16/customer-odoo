/** @odoo-module **/

import { EventBus } from "@odoo/owl";
import { afterEach, expect, test } from "@odoo/hoot";

import {
    CLOSE_REASONS,
    CONTEXT_MENU_EVENTS,
    ContextMenuCoordinator,
} from "../src/coordinator/context_menu_coordinator";
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

function makeRoot() {
    const root = document.createElement("form");
    const button = document.createElement("button");
    root.append(button);
    document.body.append(root);
    createdRoots.push(root);
    return { root, button };
}

function makeCoordinator({ definitions = [], renderMenu, routeBus, errorHandler } = {}) {
    const menuRegistry = new MenuItemRegistry();
    for (const definition of definitions) {
        menuRegistry.add(definition);
    }
    const notifications = [];
    const facade = { notification: { add: (...args) => notifications.push(args) } };
    const rendered = [];
    const coordinator = new ContextMenuCoordinator({
        menuRegistry,
        serviceFacade: facade,
        routeBus,
        errorHandler,
        renderMenu:
            renderMenu ??
            ((opening) => {
                const element = document.createElement("div");
                element.dataset.testMenu = "true";
                document.body.append(element);
                opening.element = element;
                rendered.push(opening);
                return {
                    element,
                    contains: (target) => element.contains(target),
                    destroy: () => element.remove(),
                };
            }),
    });
    activeCoordinators.push(coordinator);
    return { coordinator, menuRegistry, facade, notifications, rendered };
}

function item(id = "fixture.command", handler = () => "done", overrides = {}) {
    return {
        id,
        group: "Fixture",
        label: id,
        handler,
        ...overrides,
    };
}

function dispatchContextMenu(target, clientX = 20, clientY = 30, options = {}) {
    const event = new MouseEvent("contextmenu", {
        bubbles: true,
        cancelable: true,
        clientX,
        clientY,
        ...options,
    });
    target.dispatchEvent(event);
    return event;
}

test("resolves the nearest registered form and owns one menu at a time", () => {
    const outer = makeRoot();
    const inner = makeRoot();
    outer.root.append(inner.root);
    const { coordinator, rendered } = makeCoordinator({ definitions: [item()] });
    coordinator.registerForm(outer.root, () => ({ owner: "outer" }));
    coordinator.registerForm(inner.root, () => ({ owner: "inner" }));
    coordinator.start();

    const firstEvent = dispatchContextMenu(inner.button);
    const secondEvent = dispatchContextMenu(outer.button);

    expect(firstEvent.defaultPrevented).toBe(true);
    expect(secondEvent.defaultPrevented).toBe(true);
    expect(rendered).toHaveLength(2);
    expect(rendered[0].context.owner).toBe("inner");
    expect(rendered[1].context.owner).toBe("outer");
    expect(coordinator.openMenu.context.owner).toBe("outer");
});

test("opens from Context Menu and Shift+F10 keyboard anchors", () => {
    const { root, button } = makeRoot();
    button.getBoundingClientRect = () => ({ left: 40, right: 140, bottom: 80 });
    const { coordinator, rendered } = makeCoordinator({ definitions: [item()] });
    coordinator.registerForm(root, () => ({ owner: "keyboard-form" }));
    coordinator.start();

    const contextMenuKey = new KeyboardEvent("keydown", {
        bubbles: true,
        cancelable: true,
        key: "ContextMenu",
    });
    button.dispatchEvent(contextMenuKey);
    expect(contextMenuKey.defaultPrevented).toBe(true);
    expect(rendered[0].anchor).toEqual({ clientX: 40, clientY: 80 });
    coordinator.close();

    const shiftF10 = new KeyboardEvent("keydown", {
        bubbles: true,
        cancelable: true,
        key: "F10",
        shiftKey: true,
    });
    button.dispatchEvent(shiftF10);
    expect(shiftF10.defaultPrevented).toBe(true);
    expect(rendered[1].anchor).toEqual({ clientX: 40, clientY: 80 });
});

test("Shift + right-click preserves the native browser menu", () => {
    const { root, button } = makeRoot();
    const { coordinator, rendered } = makeCoordinator({ definitions: [item()] });
    coordinator.registerForm(root, () => ({ owner: "form" }));
    coordinator.start();

    dispatchContextMenu(button);
    expect(Boolean(coordinator.openMenu)).toBe(true);

    const nativeEvent = dispatchContextMenu(button, 20, 30, { shiftKey: true });

    expect(nativeEvent.defaultPrevented).toBe(false);
    expect(coordinator.openMenu).toBe(null);
    expect(rendered).toHaveLength(1);
});

test("preserves the native menu until a non-empty model is valid", () => {
    const { root, button } = makeRoot();
    const errors = [];
    const empty = makeCoordinator({ errorHandler: (_error, details) => errors.push(details) });
    empty.coordinator.registerForm(root, () => ({ owner: "empty" }));
    empty.coordinator.start();
    expect(dispatchContextMenu(button).defaultPrevented).toBe(false);

    const broken = makeCoordinator({
        definitions: [item("fixture.broken", () => "done", { isVisible: () => { throw new Error("broken"); } })],
        errorHandler: (_error, details) => errors.push(details),
    });
    broken.coordinator.registerForm(root, () => ({ owner: "broken" }));
    broken.coordinator.start();
    expect(dispatchContextMenu(button).defaultPrevented).toBe(false);
    expect(errors.map(({ phase }) => phase)).toEqual(["model"]);
});

test("closes on Escape, outside interaction, route changes, resize, and scroll", () => {
    const { root, button } = makeRoot();
    const routeBus = new EventBus();
    const { coordinator, rendered } = makeCoordinator({ definitions: [item()], routeBus });
    coordinator.registerForm(root, () => ({}));
    coordinator.start();
    button.focus();
    dispatchContextMenu(button);

    const insideMenu = rendered[0].element;
    insideMenu.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    expect(Boolean(coordinator.openMenu)).toBe(true);
    const escape = new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true });
    document.dispatchEvent(escape);
    expect(escape.defaultPrevented).toBe(true);
    expect(coordinator.openMenu).toBe(null);
    expect(document.activeElement).toBe(button);

    dispatchContextMenu(button);
    window.dispatchEvent(new Event("resize"));
    expect(coordinator.openMenu).toBe(null);
    dispatchContextMenu(button);
    routeBus.trigger("ROUTE_CHANGE");
    expect(coordinator.openMenu).toBe(null);
    dispatchContextMenu(button);
    window.dispatchEvent(new Event("scroll"));
    expect(coordinator.openMenu).toBe(null);
});

test("closes before invoking a command and invokes synchronous handlers once", () => {
    const { root, button } = makeRoot();
    let calls = 0;
    let wasClosed = false;
    let facadeSeen;
    const setup = makeCoordinator({
        definitions: [
            item("fixture.sync", (context, facade) => {
                calls += 1;
                wasClosed = setup.coordinator.openMenu === null;
                facadeSeen = facade;
                expect(context.anchor.clientX).toBe(20);
                return "result";
            }),
        ],
    });
    setup.coordinator.registerForm(root, () => ({ owner: "form" }));
    setup.coordinator.start();
    dispatchContextMenu(button);

    expect(setup.coordinator.execute("fixture.sync")).toBe("result");
    expect(setup.coordinator.execute("fixture.sync")).toBe(false);
    expect(calls).toBe(1);
    expect(wasClosed).toBe(true);
    expect(facadeSeen).toBe(setup.facade);
});

test("executes asynchronous handlers once and routes rejected commands safely", async () => {
    const { root, button } = makeRoot();
    let resolve;
    let calls = 0;
    const errors = [];
    const setup = makeCoordinator({
        definitions: [
            item("fixture.async", () => {
                calls += 1;
                return new Promise((done) => {
                    resolve = done;
                });
            }),
        ],
        errorHandler: (_error, details) => errors.push(details),
    });
    setup.coordinator.registerForm(root, () => ({}));
    setup.coordinator.start();
    dispatchContextMenu(button);
    const pending = setup.coordinator.execute("fixture.async");
    expect(setup.coordinator.execute("fixture.async")).toBe(false);
    expect(calls).toBe(1);
    expect(setup.coordinator.openMenu).toBe(null);
    resolve("completed");
    expect(await pending).toBe("completed");

    const failureRoot = makeRoot();
    const broken = makeCoordinator({
        definitions: [item("fixture.failure", () => { throw new Error("handler failed"); })],
        errorHandler: (_error, details) => errors.push(details),
    });
    broken.coordinator.registerForm(failureRoot.root, () => ({}));
    broken.coordinator.start();
    dispatchContextMenu(failureRoot.button);
    expect(broken.coordinator.execute("fixture.failure")).toBe(false);
    expect(errors.map(({ phase, itemId }) => [phase, itemId])).toEqual([
        ["handler", "fixture.failure"],
    ]);
    expect(setup.notifications.length + broken.notifications.length).toBe(1);
    dispatchContextMenu(failureRoot.button);
    expect(Boolean(broken.coordinator.openMenu)).toBe(true);
});

test("unregisters destroyed forms and removes all global listeners", () => {
    const { root, button } = makeRoot();
    const { coordinator } = makeCoordinator({ definitions: [item()] });
    const unregister = coordinator.registerForm(root, () => ({}));
    coordinator.start();
    dispatchContextMenu(button);
    expect(unregister()).toBe(true);
    expect(coordinator.openMenu).toBe(null);
    expect(dispatchContextMenu(button).defaultPrevented).toBe(false);

    unregister();
    coordinator.destroy();
    const later = dispatchContextMenu(button);
    expect(later.defaultPrevented).toBe(false);
    expect(coordinator.started).toBe(false);
});

test("emits lifecycle events without leaking the context snapshot into errors", () => {
    const { root, button } = makeRoot();
    const events = [];
    const { coordinator } = makeCoordinator({
        definitions: [item("fixture.error", () => Promise.reject(new Error("sensitive")))],
        errorHandler: (_error, details) => events.push(details),
    });
    coordinator.addEventListener(CONTEXT_MENU_EVENTS.OPEN, ({ detail: opening }) =>
        events.push(["open", opening.id])
    );
    coordinator.addEventListener(CONTEXT_MENU_EVENTS.CLOSE, ({ detail: { reason } }) =>
        events.push(["close", reason])
    );
    coordinator.registerForm(root, () => ({ recordCache: "must not be logged" }));
    coordinator.start();
    dispatchContextMenu(button);
    const pending = coordinator.execute("fixture.error");
    return pending.then(() => {
        expect(events[0]).toEqual(["open", 1]);
        expect(events[1]).toEqual(["close", CLOSE_REASONS.EXECUTE]);
        expect(events[2]).toEqual({ phase: "handler", itemId: "fixture.error" });
        expect(events.join(" ").includes("recordCache")).toBe(false);
        expect(events.join(" ").includes("sensitive")).toBe(false);
    });
});
