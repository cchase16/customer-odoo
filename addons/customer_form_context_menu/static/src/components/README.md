# Context-menu component

`ContextMenu` is the reusable Owl presentation shell for the framework. It
accepts the already-resolved grouped model from the coordinator and does not
evaluate predicates, call Odoo services, or contain command-specific logic.

The component provides:

- one accessible `role="menu"` with labelled `role="group"` sections and
  generated separators;
- text-only escaped labels and disabled reasons exposed through
  `aria-describedby`;
- roving focus with Arrow Up/Down, Home, End, Enter, Space, and Escape;
- mouse activation, one activation per mounted menu, and focus restoration to
  the opening target;
- fixed, viewport-clamped placement with a dialog-safe stacking level and RTL
  direction propagation.

Keyboard opening is detected by the coordinator; the component exports
`isKeyboardOpenShortcut` and `getKeyboardAnchor` helpers for the same keyboard
anchor semantics in hosts and tests. The component itself only owns the menu
after it has been opened with a valid model.
