# Customer Odoo

Deployable Odoo Community Edition customizations for this product.

This is a conventional Odoo add-ons repository. It must remain buildable, testable, and deployable without the development factory.

## Structure

- `addons/` — installable custom Odoo modules.
- `tests/` — repository-level integration, upgrade, and browser tests.
- `deployment/` — environment-independent deployment procedures and examples.
- `docs/` — product architecture and developer documentation.
- `requirements/` — pinned Python or other build-time dependency definitions.
- `factory.yaml` — human-maintained project contract with the development factory.
- `factory.lock` — generated resolution of factory policies and tooling.

Approved requirements, orchestration state, and delivery evidence are maintained in the sibling `customer-odoo-delivery` repository.
