/** @odoo-module **/

import { expect, getFixture, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import {
    computeMenuPosition,
    ContextMenu,
    getKeyboardAnchor,
    isKeyboardOpenShortcut,
} from "../src/components/context_menu";

const model = [
    {
        id: "navigation",
        label: "Navigation",
        items: [
            {
                id: "fixture.back",
                label: "Back",
                disabled: false,
                handler: () => {},
            },
            {
                id: "fixture.disabled",
                label: "Disabled command",
                disabled: true,
                disabledReason: "This command is unavailable",
                handler: () => {},
            },
        ],
    },
    {
        id: "custom",
        label: "Custom",
        items: [
            {
                id: "fixture.refresh",
                label: "Refresh",
                disabled: false,
                handler: () => {},
            },
        ],
    },
];

function keydown(target, key) {
    target.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, cancelable: true, key }));
}

test("computes a viewport-safe position and keyboard anchor", () => {
    expect(
        computeMenuPosition(
            { clientX: 790, clientY: 590 },
            { width: 800, height: 600 },
            { width: 200, height: 160 }
        )
    ).toEqual({ left: 596, top: 436 });

    const target = document.createElement("button");
    target.getBoundingClientRect = () => ({ left: 30, bottom: 48 });
    expect(getKeyboardAnchor(target, { width: 100, height: 80 })).toEqual({
        clientX: 30,
        clientY: 48,
    });
    expect(isKeyboardOpenShortcut(new KeyboardEvent("keydown", { key: "ContextMenu" }))).toBe(true);
    expect(
        isKeyboardOpenShortcut(new KeyboardEvent("keydown", { key: "F10", shiftKey: true }))
    ).toBe(true);
});

test("renders grouped accessible menu items with disabled reasons", async () => {
    await mountWithCleanup(ContextMenu, {
        props: {
            model,
            anchor: { clientX: 10, clientY: 20 },
            onExecute: () => {},
        },
    });

    expect("[role='menu']").toHaveCount(1);
    expect("[role='group']").toHaveCount(2);
    expect("[role='separator']").toHaveCount(1);
    expect("[role='menu']").toHaveAttribute("aria-label", "Context menu");
    const disabledItem = getFixture().querySelector("[role='menuitem'][aria-disabled='true']");
    expect(disabledItem.getAttribute("aria-describedby")).toMatch(/reason/);
    expect(disabledItem.textContent).toInclude("Disabled command");
    expect(disabledItem.textContent).toInclude("This command is unavailable");
});

test("supports pointer focus and activation", async () => {
    const executed = [];
    await mountWithCleanup(ContextMenu, {
        props: {
            model,
            anchor: { clientX: 10, clientY: 20 },
            onExecute: (item) => executed.push(item.id),
        },
    });

    const items = getFixture().querySelectorAll("[role='menuitem']");
    items[2].dispatchEvent(new MouseEvent("mouseenter", { bubbles: true }));
    await Promise.resolve();
    expect(document.activeElement).toBe(items[2]);

    items[2].dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    expect(executed).toEqual(["fixture.refresh"]);
});

test("supports roving keyboard focus, activation, and focus restoration", async () => {
    const focusTarget = document.createElement("button");
    document.body.append(focusTarget);
    focusTarget.focus();
    const executed = [];
    const closed = [];
    await mountWithCleanup(ContextMenu, {
        props: {
            model,
            anchor: { clientX: 10, clientY: 20 },
            focusTarget,
            onExecute: (item) => executed.push(item.id),
            onClose: (reason) => closed.push(reason),
        },
    });

    const menu = getFixture().querySelector("[role='menu']");
    await Promise.resolve();
    expect(document.activeElement).toBe(menu.querySelector("[data-menu-index='0']"));

    keydown(menu, "ArrowDown");
    await Promise.resolve();
    expect(document.activeElement).toBe(menu.querySelector("[data-menu-index='1']"));
    keydown(menu, "Enter");
    expect(executed).toEqual([]);

    keydown(menu, "ArrowDown");
    await Promise.resolve();
    keydown(menu, "Enter");
    expect(executed).toEqual(["fixture.refresh"]);

    keydown(menu, "Escape");
    await Promise.resolve();
    expect(closed).toEqual(["escape"]);
    expect(document.activeElement).toBe(focusTarget);
    focusTarget.remove();
});
