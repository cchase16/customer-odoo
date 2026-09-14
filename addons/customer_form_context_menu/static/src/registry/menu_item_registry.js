/** @odoo-module **/

import { EventBus } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const MENU_REGISTRY_CATEGORY = "customer_form_context_menu.items";
export const MENU_REGISTRY_KEY = "items";
export const DEFAULT_GROUP = "General";
export const DEFAULT_SEQUENCE = 100;
export const DEFAULT_GROUP_SEQUENCE = 100;

// These names are reserved for framework-owned menu structure and can never
// be claimed by an add-on contribution.
export const RESERVED_IDENTIFIERS = Object.freeze([
    "__separator__",
    "__group__",
    "__root__",
]);

const RESERVED_IDENTIFIER_SET = new Set(RESERVED_IDENTIFIERS);
const IDENTIFIER_PATTERN = /^[a-z][a-z0-9_.-]*$/;

export class MenuItemContractError extends Error {}
export class DuplicateMenuItemError extends MenuItemContractError {}
export class ReservedMenuItemError extends MenuItemContractError {}

function plainTextValue(value) {
    if (typeof value === "string") {
        return value;
    }
    if (value instanceof String) {
        return String.prototype.valueOf.call(value);
    }
    return null;
}

function assertText(value, field, identifier, { optional = false } = {}) {
    if (optional && value === undefined) {
        return;
    }
    const text = plainTextValue(value);
    if (text === null || !text.trim()) {
        throw new MenuItemContractError(
            `Menu item "${identifier}" requires a non-empty text ${field}`
        );
    }
}

function assertNumber(value, field, identifier) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
        throw new MenuItemContractError(
            `Menu item "${identifier}" requires a finite numeric ${field}`
        );
    }
}

function assertPredicate(value, field, identifier) {
    if (typeof value !== "function") {
        throw new MenuItemContractError(
            `Menu item "${identifier}" requires a synchronous ${field} predicate`
        );
    }
}

function assertHandler(value, identifier) {
    if (typeof value !== "function") {
        throw new MenuItemContractError(`Menu item "${identifier}" requires a handler function`);
    }
}

function assertSynchronous(value, field, identifier) {
    if (value && typeof value.then === "function") {
        throw new MenuItemContractError(
            `Menu item "${identifier}" returned an asynchronous ${field}; predicates must be synchronous`
        );
    }
    return value;
}

function normalizeDefinition(definition) {
    if (!definition || typeof definition !== "object" || Array.isArray(definition)) {
        throw new MenuItemContractError("A menu item definition must be an object");
    }

    const { id } = definition;
    if (typeof id === "string" && RESERVED_IDENTIFIER_SET.has(id)) {
        throw new ReservedMenuItemError(`Menu item identifier "${id}" is reserved`);
    }
    if (typeof id !== "string" || !IDENTIFIER_PATTERN.test(id)) {
        throw new MenuItemContractError(
            `Menu item identifier must match ${IDENTIFIER_PATTERN} (received "${id}")`
        );
    }

    const group = definition.group === undefined ? DEFAULT_GROUP : definition.group;
    assertText(group, "group", id);
    const label = definition.label;
    assertText(label, "label", id);
    const sequence = definition.sequence === undefined ? DEFAULT_SEQUENCE : definition.sequence;
    const groupSequence =
        definition.groupSequence === undefined
            ? DEFAULT_GROUP_SEQUENCE
            : definition.groupSequence;
    assertNumber(sequence, "sequence", id);
    assertNumber(groupSequence, "groupSequence", id);

    const isVisible = definition.isVisible === undefined ? () => true : definition.isVisible;
    const isEnabled = definition.isEnabled === undefined ? () => true : definition.isEnabled;
    assertPredicate(isVisible, "isVisible", id);
    assertPredicate(isEnabled, "isEnabled", id);
    assertHandler(definition.handler, id);
    if (definition.disabledReason !== undefined) {
        if (
            plainTextValue(definition.disabledReason) === null &&
            typeof definition.disabledReason !== "function"
        ) {
            throw new MenuItemContractError(
                `Menu item "${id}" requires a text or synchronous disabledReason`
            );
        }
    }
    if (definition.icon !== undefined) {
        assertText(definition.icon, "icon", id, { optional: true });
    }

    return Object.freeze({
        id,
        group,
        groupSequence,
        sequence,
        label,
        icon: definition.icon,
        isVisible,
        isEnabled,
        disabledReason: definition.disabledReason,
        handler: definition.handler,
    });
}

function sortItems(left, right) {
    return left.sequence - right.sequence || left.id.localeCompare(right.id);
}

function sortGroups(left, right) {
    return left.sequence - right.sequence || left.id.localeCompare(right.id);
}

/**
 * Registry for declarative context-menu contributions.
 *
 * Predicate evaluation accepts only a short-lived context snapshot and is
 * intentionally synchronous. The registry never invokes handlers.
 */
export class MenuItemRegistry extends EventBus {
    constructor() {
        super();
        this.items = new Map();
    }

    add(definition) {
        const item = normalizeDefinition(definition);
        if (this.items.has(item.id)) {
            throw new DuplicateMenuItemError(`Menu item identifier "${item.id}" is already registered`);
        }
        this.items.set(item.id, item);
        this.trigger("UPDATE", { operation: "add", id: item.id });
        return item;
    }

    remove(identifier) {
        if (!this.items.delete(identifier)) {
            return false;
        }
        this.trigger("UPDATE", { operation: "delete", id: identifier });
        return true;
    }

    has(identifier) {
        return this.items.has(identifier);
    }

    get(identifier) {
        return this.items.get(identifier);
    }

    getAll() {
        return [...this.items.values()].sort(sortItems);
    }

    /**
     * Build the synchronous render model for one context snapshot.
     * Hidden items and groups with no visible items are omitted.
     */
    buildModel(context = {}) {
        const groups = new Map();
        for (const definition of this.items.values()) {
            const visible = assertSynchronous(
                definition.isVisible(context),
                "visibility",
                definition.id
            );
            if (!visible) {
                continue;
            }
            const enabled = Boolean(
                assertSynchronous(definition.isEnabled(context), "enabled", definition.id)
            );
            const disabledReason = enabled
                ? undefined
                : typeof definition.disabledReason === "function"
                  ? assertSynchronous(
                        definition.disabledReason(context),
                        "disabled-reason",
                        definition.id
                    )
                  : definition.disabledReason;
            if (disabledReason !== undefined) {
                assertText(disabledReason, "disabledReason", definition.id);
            }
            const groupName = String(definition.group);
            if (!groups.has(groupName)) {
                groups.set(groupName, {
                    id: groupName,
                    label: groupName,
                    sequence: definition.groupSequence,
                    items: [],
                });
            }
            groups.get(groupName).items.push({
                id: definition.id,
                label: String(definition.label),
                icon: definition.icon,
                sequence: definition.sequence,
                disabled: !enabled,
                disabledReason:
                    disabledReason === undefined ? undefined : String(disabledReason),
                handler: definition.handler,
            });
        }

        return [...groups.values()]
            .map((group) => ({ ...group, items: group.items.sort(sortItems) }))
            .sort(sortGroups)
            .map(({ id, label, items }) => ({ id, label, items }));
    }
}

export const contextMenuRegistry = new MenuItemRegistry();
registry.category(MENU_REGISTRY_CATEGORY).add(MENU_REGISTRY_KEY, contextMenuRegistry);
