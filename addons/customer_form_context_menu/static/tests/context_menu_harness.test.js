/** @odoo-module **/

import { expect, getFixture, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import {
    ContextMenuSurfaceHarness,
    SURFACES,
    makeContextMenuFixtures,
    registerIndependentExtension,
} from "./helpers/context_menu_harness";

test("the PH-01 harness initializes the supported surface fixtures", async () => {
    await mountWithCleanup(ContextMenuSurfaceHarness, { target: getFixture() });

    expect(Boolean(getFixture().querySelector(`[data-form-root="${SURFACES.main}"]`))).toBe(true);
    expect(Boolean(getFixture().querySelector(`[data-form-root="${SURFACES.dialog}"]`))).toBe(true);
    expect(Boolean(getFixture().querySelector(`[data-form-root="${SURFACES.nested}"]`))).toBe(true);
    expect(Boolean(getFixture().querySelector(`[data-surface="${SURFACES.outside}"]`))).toBe(true);
});

test("the PH-01 harness exposes mocked services, viewport anchors, and async handlers", async () => {
    const fixtures = makeContextMenuFixtures();

    expect(Object.keys(fixtures.services)).toEqual(["action", "dialog", "notification", "orm"]);
    expect(fixtures.viewportAnchors).toHaveLength(2);
    await expect(fixtures.asyncHandler()).resolves.toBe("completed");
    expect(fixtures.calls).toEqual([["async-handler"]]);
});

test("an independent extension registers through the public fixture contract", () => {
    const contributions = [];
    registerIndependentExtension((definition) => contributions.push(definition));

    expect(contributions).toHaveLength(1);
    expect(contributions[0].id).toBe("fixture.independent.visible");
    expect(contributions[0].handler()).toBe("sync-result");
});
