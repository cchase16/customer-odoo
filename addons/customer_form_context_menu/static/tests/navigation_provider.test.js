/** @odoo-module **/

import { beforeEach, expect, test } from "@odoo/hoot";
import { patchTranslations } from "@web/../tests/web_test_helpers";

import {
    NAVIGATION_GROUP,
    NAVIGATION_IDS,
    navigationItems,
} from "../src/providers/navigation_provider";
import { MenuItemRegistry } from "../src/registry/menu_item_registry";

beforeEach(() => patchTranslations());

function makeContext({ recordId = 20, isNew = false, canPrevious = true, canNext = true } = {}) {
    const calls = [];
    return {
        context: {
            recordId,
            isNew,
            pager: { canPrevious, canNext },
            navigation: {
                back: () => calls.push("back"),
                previous: () => calls.push("previous"),
                next: () => calls.push("next"),
                refresh: () => calls.push("refresh"),
            },
        },
        calls,
    };
}

function makeRegistry() {
    const registry = new MenuItemRegistry();
    for (const item of Object.values(navigationItems)) {
        registry.add({
            id: item.id,
            group: item.group,
            groupSequence: item.groupSequence,
            sequence: item.sequence,
            label: item.label,
            isVisible: item.isVisible,
            isEnabled: item.isEnabled,
            disabledReason: item.disabledReason,
            handler: item.handler,
        });
    }
    return registry;
}

function modelFor(options) {
    const model = makeRegistry().buildModel(makeContext(options).context);
    return model[0].items;
}

test("registers the four navigation commands in a deterministic group and order", () => {
    expect(navigationItems.back.group).toBe(NAVIGATION_GROUP);
    expect(Object.keys(navigationItems)).toEqual(["back", "previous", "next", "refresh"]);
    expect(Object.values(navigationItems).map((item) => item.id)).toEqual([
        NAVIGATION_IDS.back,
        NAVIGATION_IDS.previous,
        NAVIGATION_IDS.next,
        NAVIGATION_IDS.refresh,
    ]);
});

test("keeps navigation commands visible and guards new-record navigation", () => {
    const items = modelFor({ recordId: false, isNew: true, canPrevious: false, canNext: false });

    expect(items).toHaveLength(4);
    expect(items.map((item) => item.disabled)).toEqual([false, true, true, true]);
    expect(items.map((item) => item.label)).toEqual([
        "Back",
        "Previous record",
        "Next record",
        "Refresh record",
    ]);
    expect(items.slice(1).every((item) => item.disabledReason)).toBe(true);
});

test("enables the correct commands at the first, middle, and last records", () => {
    expect(modelFor({ canPrevious: false, canNext: true }).map((item) => item.disabled)).toEqual([
        false,
        true,
        false,
        false,
    ]);
    expect(modelFor({ canPrevious: true, canNext: true }).map((item) => item.disabled)).toEqual([
        false,
        false,
        false,
        false,
    ]);
    expect(modelFor({ canPrevious: true, canNext: false }).map((item) => item.disabled)).toEqual([
        false,
        false,
        true,
        false,
    ]);
});

test("handlers delegate to the navigation facade without changing dirty state", () => {
    const { context, calls } = makeContext({ canPrevious: true, canNext: true });
    for (const item of Object.values(navigationItems)) {
        item.handler(context, {});
    }
    expect(calls).toEqual(["back", "previous", "next", "refresh"]);
    expect(context.dirty).toBe(undefined);
});

test("dirty persisted records retain guarded navigation eligibility", () => {
    const { context } = makeContext({ canPrevious: true, canNext: true });
    context.dirty = true;
    const items = makeRegistry().buildModel(context)[0].items;

    expect(items.map((item) => item.disabled)).toEqual([false, false, false, false]);
    expect(items.map((item) => item.handler)).toHaveLength(4);
});
