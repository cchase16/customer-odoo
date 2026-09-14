# Frontend boundary

The add-on's release-sensitive Odoo web-client access belongs in
`adapter/`. Shared lifecycle and rendering code belongs in `coordinator/`,
`components/`, and `services/`. Command behavior belongs in independently
removable `providers/` modules.

The add-on has no models, controllers, routes, or RPC calls during menu
opening. Navigation and extension behavior are independently removable provider
contributions and delegate operations through the public service facade.
