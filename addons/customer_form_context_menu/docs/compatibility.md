# PH-01 compatibility record

This record captures the executable product context discovered before feature
implementation. It is intentionally separate from the approved run plan.

## Product and deployment

- Product contract: `factory.yaml` identifies an Odoo add-ons repository,
  the current generic prefix `CW` (`cw_` for Odoo technical module names),
  LGPL-3 licensing, and `addons/` as the add-on path. This add-on's existing
  `customer_` prefix is a retained legacy exception, not the naming convention.
- Reference product baseline: `39082176e3b543792bc78c028a4eaf091f9548bf`.
- Odoo source: `E:\Dev\Odoo\Odoo-19.0`.
- Runtime command: `C:\Program Files\Odoo 19.0.20260802\python\python.exe`.
- Runtime result: `Odoo Server 19.0-20260802`.
- Source `odoo/release.py`: Community-compatible Odoo `19.0`, build
  `20260802`, native source head `869c750f978b1b00a4a04bd61226f0e20d2e7729`.
- Development invocation: `Start_OD_Dev.ps1` uses database `OD_Dev` on
  `127.0.0.1:8070`; PH-01 installation validation used the disposable
  database `customer_odoo_ph01` on `127.0.0.1:8071`.

The deployed release matches the approved Odoo 19.0 Community reference
baseline. No product add-ons existed before this scaffold, so no existing
product frontend extension or context-menu override was found.

## Observed Odoo 19 APIs for the adapter boundary

| Concern | Observed API | Adapter implication |
| --- | --- | --- |
| Form ownership/lifecycle | `FormController.rootRef`, `onMounted`, `onWillUnmount`, and `env.inDialog` | Register roots at lifecycle boundaries; keep controller access in the adapter. |
| Dirty/new guards | `beforeLeave({ forceLeave })`, `model.root.isDirty()`, `model.root.isNew`, and `model.root.save()` | Delegate navigation guards; never clear dirty state or discard directly. |
| Record reload/pager | `model.load({ resId, resIds })`, `model.root.resIds`, `usePager`, and `onPagerUpdate` | Expose safe reload and previous/next operations through the facade. |
| Action stack/navigation | `actionService.doAction`, `switchView`, `restore`, `currentController`, and `currentAction` | Use the service facade; do not mutate routes or the action stack directly. |
| Dialogs | `dialogService.add(Component, props, options)` and returned close callback | Use the standard dialog service for modal commands. |
| Notifications | `notification` service via `useService("notification")` | Route user-facing command failures through the standard notification service. |
| Server access | `orm` service via `useService("orm")` | No RPC during menu construction; server authorization remains authoritative. |

## Browser matrix and conflicts

The organization did not provide a supported desktop-browser policy in the
product, deployment, or development-factory repositories. The machine has
Chrome `151.0.7922.172` and Edge `152.0.4191.66`; Firefox is not installed.
These are observed automation targets, not an asserted support policy. The
missing policy is an explicit blocker for the later browser-acceptance gate
until an authorized owner records the supported matrix.

No third-party add-ons or custom `contextmenu`/form-controller patches were
discoverable in the isolated product repository. Interceptor precedence must
therefore be validated against the actual customer deployment before release.

## Test commands and PH-01 results

- Manifest syntax/contract check: passed.
- Static scaffold security check for dynamic evaluation: passed.
- Browser surface smoke runner:
  `powershell -NoProfile -ExecutionPolicy Bypass -File
  addons/customer_form_context_menu/tests/browser/run-scaffold-smoke.ps1` —
  passed.
- Clean install on `customer_odoo_ph01`: passed; module state is `installed`.
- Module update from the same disposable database: passed.
- Backend smoke via the local Odoo server: signed in as `admin`, opened the
  Users form (`/odoo/users`, one `.o_form_view`), with zero console/page
  errors.
- HOOT harness filters `PH-01 harness` and `independent extension`: passed;
  3 scaffold tests, 12 assertions total across both runs.

The scaffold introduces no models, access-control files, controllers,
endpoints, migrations, event listeners, RPC calls, or Enterprise dependency.
