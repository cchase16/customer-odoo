/** @odoo-module */

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

const LIVE_NOTIFICATION = "cw_custom_alert.notification";

export function buildAlertChannel(userId) {
    return `cw_custom_alerts.user.${userId}`;
}

export function normalizeInboxState(inbox) {
    return {
        count: Number.isFinite(inbox?.count) ? inbox.count : 0,
        notifications: Array.isArray(inbox?.notifications) ? inbox.notifications : [],
    };
}

export const customAlertInboxService = {
    dependencies: ["orm", "bus_service", "notification"],

    start(env, { orm, bus_service: busService, notification }) {
        const state = reactive({ count: 0, notifications: [], ready: false });
        const channel = buildAlertChannel(user.userId);

        async function refresh() {
            try {
                const inbox = await orm.call("alert.notification", "get_inbox_state", []);
                const normalized = normalizeInboxState(inbox);
                state.count = normalized.count;
                state.notifications = normalized.notifications;
                state.ready = true;
            } catch {
                // The persistent inbox is authoritative.  A temporary RPC
                // outage must not manufacture client-side alert state.
            }
            return state;
        }

        function onLiveNotification(payload) {
            void refresh();
            if (payload?.message) {
                notification.add(payload.message, {
                    title: payload.subject || "Custom alert",
                    type: payload.severity || "info",
                });
            }
        }

        busService.subscribe(LIVE_NOTIFICATION, onLiveNotification);
        void busService.addChannel(channel);
        void refresh();

        return {
            state,
            refresh,
            async markRead(id) {
                await orm.call("alert.notification", "mark_read", [[id]]);
                return refresh();
            },
            async markAllRead() {
                await orm.call("alert.notification", "mark_all_read", []);
                return refresh();
            },
            open(id) {
                return orm.call("alert.notification", "action_open_source", [[id]]);
            },
        };
    },
};

registry.category("services").add("cw_alert_inbox", customAlertInboxService);
