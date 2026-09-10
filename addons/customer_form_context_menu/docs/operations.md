# Operations runbook

## Environment

The reference deployment is Odoo Community 19.0, build `20260802`, using the
`customer_form_context_menu` add-on and `web` as its only manifest dependency.
The observed automation matrix is Chrome 151 and Edge 152. The product owner
has not supplied an organizational browser policy; record that policy before
release acceptance.

## Install and update

On a disposable nonproduction database, add the module path, install
`customer_form_context_menu`, rebuild backend assets, and run the module and
browser checks. For an existing installation, update the module, rebuild the
same assets, and repeat the checks. Record the exact product commit, database
lineage, Odoo build, browser versions, commands, screenshots, console output,
and results with the delivery workflow.

The module has no models, persistent tables, access-control files, controllers,
endpoints, or migrations. Installation and update therefore require no schema
change. Menu construction and predicate evaluation must remain offline; server
authorization remains delegated to Odoo services.

Useful local checks from the product worktree are:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File addons/customer_form_context_menu/tests/browser/run-scaffold-smoke.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File addons/customer_form_context_menu/tests/browser/run-acceptance.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File addons/customer_form_context_menu/tests/browser/run-quality-checks.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File addons/customer_form_context_menu/tests/browser/run-hardening-checks.ps1
```

## Staged monitoring and rollback

During staged rollout monitor frontend initialization errors, command failures,
duplicate menus, listener or stale-registration symptoms, and reports that the
browser context menu disappeared outside supported forms. If a rollback trigger
fires, disable or uninstall the module, rebuild backend assets, and verify that
native browser menus return inside forms while outside-form behavior is
unchanged. No database migration or persistent-data cleanup is required.

Restore the module only after the failure is understood and the same smoke,
acceptance, quality, and hardening checks pass. Human approvals and release
authorization remain outside this runbook and must be recorded only by
authorized people.
