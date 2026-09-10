/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

const VIEWPORT_MARGIN = 4;
const FALLBACK_MENU_SIZE = Object.freeze({ width: 280, height: 320 });
const FALLBACK_VIEWPORT = Object.freeze({ width: 1024, height: 768 });
let nextMenuId = 1;

export function isKeyboardOpenShortcut(event) {
    return event.key === "ContextMenu" || (event.key === "F10" && event.shiftKey);
}

export function getKeyboardAnchor(target, viewport = {}, direction = "ltr") {
    const rect = target?.getBoundingClientRect?.() ?? { left: 0, bottom: 0 };
    const width = Number(viewport.width ?? globalThis.innerWidth) || FALLBACK_VIEWPORT.width;
    const height = Number(viewport.height ?? globalThis.innerHeight) || FALLBACK_VIEWPORT.height;
    return Object.freeze({
        clientX: Math.max(
            0,
            Math.min(Number(direction === "rtl" ? rect.right ?? rect.left : rect.left) || 0, width)
        ),
        clientY: Math.max(0, Math.min(Number(rect.bottom) || 0, height)),
    });
}

export function computeMenuPosition(anchor, viewport, menuSize = FALLBACK_MENU_SIZE) {
    const viewportWidth = Math.max(
        0,
        Number(viewport?.width) || FALLBACK_VIEWPORT.width
    );
    const viewportHeight = Math.max(
        0,
        Number(viewport?.height) || FALLBACK_VIEWPORT.height
    );
    const width = Math.max(
        0,
        Math.min(Number(menuSize?.width) || FALLBACK_MENU_SIZE.width, viewportWidth - VIEWPORT_MARGIN * 2)
    );
    const height = Math.max(
        0,
        Math.min(Number(menuSize?.height) || FALLBACK_MENU_SIZE.height, viewportHeight - VIEWPORT_MARGIN * 2)
    );
    return Object.freeze({
        left: Math.max(
            VIEWPORT_MARGIN,
            Math.min(Number(anchor?.clientX) || 0, viewportWidth - width - VIEWPORT_MARGIN)
        ),
        top: Math.max(
            VIEWPORT_MARGIN,
            Math.min(Number(anchor?.clientY) || 0, viewportHeight - height - VIEWPORT_MARGIN)
        ),
    });
}

function countItems(groups) {
    return groups.reduce((total, group) => total + group.items.length, 0);
}

export class ContextMenu extends Component {
    static template = "customer_form_context_menu.ContextMenu";
    static defaultProps = {
        ariaLabel: "Context menu",
    };
    static props = {
        model: { type: Array },
        anchor: { type: Object },
        onExecute: { type: Function },
        onClose: { type: Function, optional: true },
        focusTarget: { type: Object, optional: true },
        direction: { type: String, optional: true },
        ariaLabel: { type: String, optional: true },
    };

    setup() {
        this.menuRef = useRef("menu");
        this.menuId = `customer-context-menu-${nextMenuId++}`;
        this.focusTarget = this.props.focusTarget ?? document.activeElement;
        this.state = useState({
            focusedIndex: this.items.length ? 0 : -1,
            closed: false,
            activatedIndex: -1,
            position: { left: VIEWPORT_MARGIN, top: VIEWPORT_MARGIN },
        });
        this._boundReposition = () => this.reposition();
        onMounted(() => {
            window.addEventListener("resize", this._boundReposition);
            window.addEventListener("scroll", this._boundReposition, true);
            this.reposition();
            this.focusCurrent();
        });
        onWillUnmount(() => {
            window.removeEventListener("resize", this._boundReposition);
            window.removeEventListener("scroll", this._boundReposition, true);
            if (!this.state.closed) {
                this.restoreFocus();
            }
        });
    }

    get groups() {
        return this.props.model.map((group, index) => ({
            ...group,
            separator: index > 0,
        }));
    }

    get items() {
        return this.props.model.flatMap((group) => group.items);
    }

    get direction() {
        return this.props.direction || document.documentElement.dir || "ltr";
    }

    get ariaLabel() {
        return this.props.ariaLabel || "Context menu";
    }

    get positionStyle() {
        return `left: ${this.state.position.left}px; top: ${this.state.position.top}px;`;
    }

    reasonId(item) {
        return `${this.menuId}-reason-${item.id}`;
    }

    itemId(index) {
        return `${this.menuId}-item-${index}`;
    }

    itemTabIndex(index) {
        return this.state.focusedIndex === index ? 0 : -1;
    }

    itemClass(item, index) {
        return [
            "o_customer_context_menu_item",
            this.state.focusedIndex === index ? "is-focused" : "",
            item.disabled ? "is-disabled" : "",
        ]
            .filter(Boolean)
            .join(" ");
    }

    reposition() {
        const menu = this.menuRef.el;
        if (!menu) {
            return;
        }
        const width = window.innerWidth || document.documentElement.clientWidth || 1024;
        const height = window.innerHeight || document.documentElement.clientHeight || 768;
        const rect = menu.getBoundingClientRect();
        this.state.position = computeMenuPosition(
            this.props.anchor,
            { width, height },
            {
                width: rect.width || FALLBACK_MENU_SIZE.width,
                height: rect.height || Math.max(80, countItems(this.props.model) * 40),
            }
        );
    }

    focusCurrent() {
        const index = this.state.focusedIndex;
        const target = this.menuRef.el?.querySelector(`[data-menu-index="${index}"]`);
        (target || this.menuRef.el)?.focus?.({ preventScroll: true });
    }

    focusItem(index) {
        if (index < 0 || index >= this.items.length) {
            return;
        }
        this.state.focusedIndex = index;
        Promise.resolve().then(() => this.focusCurrent());
    }

    moveFocus(delta) {
        if (!this.items.length) {
            return;
        }
        const current = this.state.focusedIndex < 0 ? 0 : this.state.focusedIndex;
        this.focusItem((current + delta + this.items.length) % this.items.length);
    }

    activate(index = this.state.focusedIndex) {
        const item = this.items[index];
        if (!item || item.disabled || this.state.activatedIndex !== -1 || this.state.closed) {
            return false;
        }
        this.state.activatedIndex = index;
        this.props.onExecute(item);
        return true;
    }

    close(reason = "escape") {
        if (this.state.closed) {
            return false;
        }
        this.state.closed = true;
        this.props.onClose?.(reason);
        this.restoreFocus();
        return true;
    }

    restoreFocus() {
        if (this.focusRestored) {
            return;
        }
        this.focusRestored = true;
        const focusTarget = this.focusTarget;
        Promise.resolve().then(() => {
            if (focusTarget && focusTarget.isConnected !== false) {
                focusTarget.focus?.({ preventScroll: true });
            }
        });
    }

    onKeydown(event) {
        if (event.key === "ArrowDown") {
            event.preventDefault();
            event.stopPropagation();
            this.moveFocus(1);
        } else if (event.key === "ArrowUp") {
            event.preventDefault();
            event.stopPropagation();
            this.moveFocus(-1);
        } else if (event.key === "Home") {
            event.preventDefault();
            event.stopPropagation();
            this.focusItem(0);
        } else if (event.key === "End") {
            event.preventDefault();
            event.stopPropagation();
            this.focusItem(this.items.length - 1);
        } else if (event.key === "Enter" || event.key === " " || event.key === "Spacebar") {
            event.preventDefault();
            event.stopPropagation();
            this.activate();
        } else if (event.key === "Escape") {
            event.preventDefault();
            event.stopPropagation();
            this.close("escape");
        }
    }

    onItemClick(item, index, event) {
        event.preventDefault();
        event.stopPropagation();
        this.focusItem(index);
        this.activate(index);
    }
}
