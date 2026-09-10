# Providers

Providers are independently removable registry contributions. The navigation
provider registers Back, Previous record, Next record, and Refresh record in
the `Navigation` group. It uses only the short-lived context snapshot and the
public `navigation` facade supplied by the release-specific form adapter.

Navigation availability is synchronous and local: Back remains available so
the adapter can apply Odoo's dirty-form guard, while Refresh requires a
persisted record and Previous/Next additionally require the matching pager
state. Handlers never clear dirty state or discard records; the Odoo adapter
owns the standard dirty-form guards.

The Main Table placeholder is a separate `Custom`-group contribution. Its
callback opens a standard Odoo modal with the exact body `Go to the Main Table
form` and one `Close` action; it deliberately performs no navigation. Future
Main Table navigation belongs in this provider callback, not in the
framework.

The test-only `customer_form_context_menu_test_extension` add-on demonstrates
that an independent module can register visible, hidden, enabled, disabled,
synchronous, asynchronous, existing-group, namespaced-group, and failing
commands through the same public registry. It has no backend asset and does
not import form-controller internals.
