# Odoo 19 adapter boundary

Release-sensitive automation mapping and list/form context capture belong in
this boundary. Stable rule, event, comparison, security, occurrence, and
delivery contracts must not import private Odoo web-client or automation
internals. Implementations are intentionally deferred to later phases.
