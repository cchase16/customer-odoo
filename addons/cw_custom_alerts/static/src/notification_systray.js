/** @odoo-module */

import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CustomAlertInbox extends Component {
    static template = "cw_custom_alerts.CustomAlertInbox";
    static components = { Dropdown, DropdownItem };
    static props = {};

    setup() {
        this.inbox = useService("cw_alert_inbox");
        this.action = useService("action");
        this.state = this.inbox.state;
    }

    async markAllRead() {
        await this.inbox.markAllRead();
    }

    async openAlert(alert) {
        await this.inbox.markRead(alert.id);
        const action = await this.inbox.open(alert.id);
        return this.action.doAction(action);
    }

    async viewAll() {
        return this.action.doAction("cw_custom_alerts.action_alert_notifications");
    }
}

registry.category("systray").add(
    "cw_custom_alerts.inbox",
    { Component: CustomAlertInbox },
    { sequence: 102 }
);
