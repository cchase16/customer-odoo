# Configuration validation contract

`models/validation.py` is the release-independent safety boundary for rule
configuration. It accepts JSON snapshots and Odoo field metadata, then either
raises `AlertConfigurationError` or returns copied, canonical domain values.

Domains are limited to 100 tokens, 50 conditions, three field-path
components, and 100 values in an `in`/`not in` condition. Traversal can cross
only stored many-to-one fields and a final field must be stored and
scalar-compatible or many-to-one.
Binary, HTML, collection, transient, abstract, non-stored, and executable
configuration is rejected.

The only message placeholders are `${rule_name}`, `${model_name}`,
`${record_name}`, `${field_name}`, `${old_value}`, `${new_value}`, and
`${event_time}`. Rendering is plain text; no template language is evaluated.
