# Security and compatibility checklist

- [x] No dynamic source evaluation (`eval` or `new Function`).
- [x] No raw-HTML label or reason rendering.
- [x] No direct network request during menu construction or predicate checks.
- [x] Command handlers use the constrained Odoo service facade.
- [x] Server authorization and record rules remain authoritative.
- [x] Context snapshots are short-lived and custom errors omit form values and
      record caches.
- [x] The coordinator closes before execution, guards exactly-once execution,
      removes global listeners, and restores focus.
- [x] Third-party `contextmenu` interception is deterministic: an earlier
      capture listener that marks the event handled retains native ownership;
      the coordinator does not cancel or open a menu for that event.
- [x] After coordinator cleanup, form events retain native browser behavior.

The automated hardening runner checks the source controls and executes the
conflict/lifecycle fixture in Chrome and Edge. Customer-specific add-ons may
still patch form internals or event precedence; representative combinations
must be tested in the target deployment before release acceptance.

The add-on intentionally does not make client-only authorization decisions.
Providers should surface availability from the short-lived context and allow
Odoo's action, ORM, dialog, and dirty-form guards to enforce authorization and
data-safety decisions.
