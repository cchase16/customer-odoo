/** @odoo-module **/

import { Component, xml } from "@odoo/owl";

export const SURFACES = Object.freeze({
    main: "main-form",
    dialog: "dialog-form",
    nested: "nested-form",
    outside: "outside-surface",
});

export class ContextMenuSurfaceHarness extends Component {
    static template = xml`
        <div class="o_context_menu_harness">
            <section data-surface="main-form">
                <form data-form-root="main-form">
                    <input aria-label="Main form field" />
                    <div data-surface="nested-form">
                        <div data-form-root="nested-form">
                            <input aria-label="Nested form field" />
                        </div>
                    </div>
                </form>
            </section>
            <div role="dialog" data-surface="dialog-form">
                <form data-form-root="dialog-form">
                    <textarea aria-label="Dialog form field" />
                </form>
            </div>
            <section data-surface="outside-surface">
                <button type="button">Outside form</button>
            </section>
        </div>
    `;
}

export function makeContextMenuFixtures() {
    const calls = [];
    return {
        calls,
        services: {
            action: { doAction: (...args) => calls.push(["action", args]) },
            dialog: { add: (...args) => calls.push(["dialog", args]) },
            notification: { add: (...args) => calls.push(["notification", args]) },
            orm: { call: (...args) => calls.push(["orm", args]) },
        },
        viewportAnchors: [
            { name: "top-left", clientX: 0, clientY: 0 },
            { name: "bottom-right", clientX: 1279, clientY: 719 },
        ],
        asyncHandler: async () => {
            calls.push(["async-handler"]);
            return "completed";
        },
    };
}

export function registerIndependentExtension(register) {
    register({
        id: "fixture.independent.visible",
        group: "Fixture",
        sequence: 10,
        label: "Independent visible command",
        isVisible: () => true,
        isEnabled: () => true,
        handler: () => "sync-result",
    });
}
