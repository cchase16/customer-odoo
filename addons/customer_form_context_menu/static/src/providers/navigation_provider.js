/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

import { contextMenuRegistry } from "../registry/menu_item_registry";

export const NAVIGATION_GROUP = "Navigation";
export const NAVIGATION_GROUP_SEQUENCE = 10;

export const NAVIGATION_IDS = Object.freeze({
    back: "customer_form_context_menu.navigation.back",
    previous: "customer_form_context_menu.navigation.previous",
    next: "customer_form_context_menu.navigation.next",
    refresh: "customer_form_context_menu.navigation.refresh",
});

function isPersistedRecord(context) {
    return Boolean(context?.recordId) && !context?.isNew;
}

function pagerState(context) {
    return context?.pager ?? {};
}

function navigationOperation(context, operation) {
    const handler = context?.navigation?.[operation];
    return typeof handler === "function" ? handler() : false;
}

function addNavigationItem(definition) {
    return contextMenuRegistry.add({
        group: NAVIGATION_GROUP,
        groupSequence: NAVIGATION_GROUP_SEQUENCE,
        ...definition,
    });
}

export const navigationItems = Object.freeze({
    back: addNavigationItem({
        id: NAVIGATION_IDS.back,
        sequence: 10,
        label: _t("Back"),
        isVisible: () => true,
        isEnabled: () => true,
        handler: (context) => navigationOperation(context, "back"),
    }),
    previous: addNavigationItem({
        id: NAVIGATION_IDS.previous,
        sequence: 20,
        label: _t("Previous record"),
        isVisible: () => true,
        isEnabled: (context) => isPersistedRecord(context) && Boolean(pagerState(context).canPrevious),
        disabledReason: (context) =>
            context?.isNew
                ? _t("Previous record is unavailable for a new record.")
                : _t("This is the first record."),
        handler: (context) => navigationOperation(context, "previous"),
    }),
    next: addNavigationItem({
        id: NAVIGATION_IDS.next,
        sequence: 30,
        label: _t("Next record"),
        isVisible: () => true,
        isEnabled: (context) => isPersistedRecord(context) && Boolean(pagerState(context).canNext),
        disabledReason: (context) =>
            context?.isNew
                ? _t("Next record is unavailable for a new record.")
                : _t("This is the last record."),
        handler: (context) => navigationOperation(context, "next"),
    }),
    refresh: addNavigationItem({
        id: NAVIGATION_IDS.refresh,
        sequence: 40,
        label: _t("Refresh record"),
        isVisible: () => true,
        isEnabled: isPersistedRecord,
        disabledReason: _t("Refresh is unavailable for a new record."),
        handler: (context) => navigationOperation(context, "refresh"),
    }),
});
