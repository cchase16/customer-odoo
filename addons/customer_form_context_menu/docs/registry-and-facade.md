# Registry and service facade contract

The public menu registry is the `contextMenuRegistry` export from
`static/src/registry/menu_item_registry.js`. Independent add-ons register a
definition with a stable, namespaced `id`, a text `label`, a text `group`, a
numeric `sequence`, and a synchronous `handler`:

```js
import { contextMenuRegistry } from
    "@customer_form_context_menu/static/src/registry/menu_item_registry";

contextMenuRegistry.add({
    id: "my_addon.example_command",
    group: "Custom",
    sequence: 20,
    label: "Example command",
    isVisible: (context) => context.canUseExample,
    isEnabled: (context) => context.isPersisted,
    disabledReason: "This command needs a saved record",
    handler: (context, services) => services.action.doAction("my_action"),
});
```

Definitions default to the `General` group, sequence `100`, visible, and
enabled. Visible items are grouped by `groupSequence` then group identifier;
items are ordered by `sequence` then identifier. Hidden items and empty groups
are omitted. Duplicate and framework-reserved identifiers are rejected.

`isVisible`, `isEnabled`, and function-valued `disabledReason` receive only a
short-lived context snapshot and must return synchronously. They must not call
RPC or return a Promise. Labels, groups, icons, and disabled reasons are plain
text; the framework does not evaluate source strings or render raw HTML.

The `context_menu` service exposes only `getItems`, constrained action methods
(`doAction`, `doActionButton`, `switchView`, `restore`), dialog `add` and
`closeAll`, notification `add`, ORM `call`, and the form adapter's navigation
facade. Providers receive that facade as the second handler argument. They must
not retain or mutate the underlying Odoo service objects.
