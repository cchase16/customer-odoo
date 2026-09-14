# Extension guide

An independent add-on contributes commands by importing the public registry and
adding a definition. It does not import a form controller, create a competing
menu shell, or edit this module's coordinator:

```js
import { contextMenuRegistry } from
    "@customer_form_context_menu/registry/menu_item_registry";

contextMenuRegistry.add({
    id: "my_addon.export_record",
    group: "Custom",
    groupSequence: 20,
    sequence: 30,
    label: "Export record",
    isVisible: (context) => Boolean(context.recordId),
    isEnabled: (context) => !context.isDirty,
    disabledReason: "Save the record before exporting.",
    handler: (_context, services) => services.action.doAction("my_export_action"),
});
```

Identifiers must be stable and namespaced. Labels, groups, icons, and reasons
are plain text. Predicates are synchronous, inexpensive, and local-only; they
must not make RPCs or return promises. Handlers may be synchronous or
asynchronous and must use only the documented facade. The coordinator closes
the menu before execution, invokes a selected item at most once, and routes a
failed item without corrupting other registrations.

The built-in Navigation items are ordinary registry contributions. Additional
commands, such as the Alerts contribution, remain independently removable and
do not add command-specific branches to the framework.

Browser editing, spelling, and inspection commands are not reproduced by the
custom menu. Users can retain those workflows with keyboard shortcuts or use
Shift + right-click to bypass the custom menu and open the native browser menu.
