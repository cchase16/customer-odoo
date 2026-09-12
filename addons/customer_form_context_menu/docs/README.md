# Customer Form Context Menu

This standalone add-on is the implementation boundary for the approved
reusable backend form context-menu run plan. Its `customer_` prefix predates
the current `CW`/`cw_` naming convention and is retained as a compatibility
exception; it is not a precedent for new add-ons.

The initial implementation contains a reusable form context-menu framework,
Navigation commands, and a removable Main Table placeholder. Release-sensitive
form-controller access remains in one adapter; command behavior is contributed
through the public registry without adding models, controllers, endpoints,
migrations, or Enterprise dependencies.

See [extension-guide.md](extension-guide.md),
[security-and-compatibility.md](security-and-compatibility.md), and
[operations.md](operations.md) for extension, review, rollout, and rollback
guidance.
