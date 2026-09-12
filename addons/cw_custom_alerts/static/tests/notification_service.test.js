/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import { buildAlertChannel, normalizeInboxState } from "../src/notification_service";

test("alert inbox uses a per-user bus channel", () => {
    expect(buildAlertChannel(42)).toBe("cw_custom_alerts.user.42");
});

test("inbox refresh accepts only the server-provided durable shape", () => {
    const alerts = [{ id: 7, subject: "A", message: "B" }];
    expect(normalizeInboxState({ count: 1, notifications: alerts })).toEqual({
        count: 1,
        notifications: alerts,
    });
    expect(normalizeInboxState({ count: "1", notifications: null })).toEqual({
        count: 0,
        notifications: [],
    });
});
