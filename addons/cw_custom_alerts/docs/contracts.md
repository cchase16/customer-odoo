# Custom-alerts internal contracts

`models/contracts.py` is the release-independent seam for the alert engine.
It contains immutable data transfer objects and Python protocols only; it does
not import Odoo or expose recordsets, controllers, services, or client models.

The boundary is split as follows:

`SUPPORTED_EVENT_TYPES` explicitly covers record-created and record-deleted
events, stored-field changed/becomes/is-no-longer/postponed/advanced events,
and reached or relative-before/relative-after date events. The value and
comparison semantics remain implementation responsibilities of later phases.

| Contract | Owner | Adapter boundary |
| --- | --- | --- |
| `RuleSpec`, `EventContext` | Rule/event engine | ORM normalization in the Odoo model layer |
| `Comparator` | Generic comparison engine | Field metadata and Odoo values supplied by caller |
| `RecipientContext`, `SecurityPolicy` | Security and privacy layer | User/company/access checks in the ORM layer |
| `NotificationDraft`, `NotificationRenderer` | Safe rendering | Plain-text placeholder service; no executable template |
| `OccurrenceIdentity`, `OccurrenceKeyBuilder` | Date idempotency | Controlled clock and database uniqueness implementation |
| `AutomationBinding`, `AutomationMapper` | Automation integration | Odoo 19 `base_automation` / server-action mapper only |
| `DeliverySink` | Durable/live delivery | ORM transaction, post-commit bus, and optional mail queue |
| `CapturedContext`, `ContextAdapter` | Page context transfer | Odoo 19 list/form client adapter only |

The frontend `static/src/contracts.js` mirrors only the JSON-safe context
transfer shape. It deliberately excludes controller, model, recordset, and
service objects. Server-side authorization must revalidate all identifiers
before a rule is created; the client contract is not an authorization grant.

Later phases may add implementations under `models/`, `wizard/`, and isolated
Odoo 19 adapter packages. They must consume these contracts without adding
model-specific sales or purchase branches to the generic evaluator.

## PH-01 design review

The contracts were reviewed against the approved design decisions and the
FR01-FR22 scope at the boundary level:

- rule lifecycle, event inputs, comparison outcomes, and date occurrences are
  represented without tying them to an Odoo recordset;
- recipient ownership, company context, fresh source access, and safe
  navigation metadata have an explicit security boundary;
- notification content is a rendered plain-text draft, with no expression,
  template, HTML, SQL, or executable-content contract;
- persistence, post-commit bus publication, and optional mail queuing are
  separate delivery responsibilities, keeping the inbox authoritative;
- the context transfer is JSON-safe and server-revalidated, so client-supplied
  identifiers cannot act as authorization;
- automation mapping and list/form context capture are the only named
  release-sensitive adapters, and their internals are not imported by the
  stable contracts; and
- the module remains an independently installable `cw_custom_alerts` addon
  with the approved Community dependencies and no product-specific sales or
  purchase branch.

This review establishes the phase boundary only. Models, validation behavior,
automation synchronization, UI, delivery, and acceptance scenarios remain
unimplemented work for later approved phases.
