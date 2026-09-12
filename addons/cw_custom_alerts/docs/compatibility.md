# PH-01 compatibility record

This module-local record captures the repository and runtime findings for
`RP-8039BD31C87E86D26E1E` revision 1 at product baseline
`6ee1bfb7d7ab3547f9b6c8a15452bede596cbe53`.

## Confirmed target and naming

- Odoo target: Community Edition 19.0, build 20260802.
- Odoo source: `E:\Dev\Odoo\Odoo-19.0`.
- Odoo runtime: `C:\Program Files\Odoo 19.0.20260802\python\python.exe`.
- Runtime probe: `Odoo Server 19.0-20260802`; Python 3.12.3.
- Product add-on path: `addons/`; each direct child is an independently
  installable module with a Python `__manifest__.py` and `__init__.py`.
- Naming: `CW` / `cw_` from `factory.yaml`; this module is `cw_custom_alerts`.
- License: LGPL-3.

## Repository conventions discovered

- Manifests use Python dictionary literals with `name`, `summary`, `version`,
  `category`, `license`, `depends`, `data`, `assets`, `installable`, and
  `application` keys.
- Backend JavaScript is declared in `web.assets_backend`; HOOT files are
  declared in `web.assets_unit_tests` and normally use a `static/tests/`
  tree. Owl/web helpers are imported from Odoo aliases such as
  `@odoo/hoot` and `@web/../tests/web_test_helpers`.
- Existing product frontend code is isolated below `static/src/` and uses
  small registry, service, adapter, component, and provider directories.
- Existing product translations use `i18n/<module>.pot`.
- No product Python models, controllers, migrations, or `base_automation`
  extensions existed at this baseline. The new module must therefore keep
  its future automation mapper isolated and must not modify Odoo core or the
  legacy `customer_` modules.

## Commands and environments

The product repository has no root `package.json`, pytest configuration, or
dedicated lint/manifest runner. The following repository-supported commands
and Odoo-native commands are the phase-appropriate targets:

| Gate or check | Command / target | Status |
| --- | --- | --- |
| Manifest validation | Python compile plus manifest load using the pinned Odoo Python | Available |
| Lint | No repository runner is configured; use the pinned Python compile/static checks and record any external factory lint result | External runner required |
| Python unit tests | Odoo `server --test-enable --test-tags /cw_custom_alerts` against a disposable database | Available when PostgreSQL is provisioned |
| HOOT tests | Odoo `/web/tests?headless&loglevel=2&preset=desktop` with the module installed and `web.assets_unit_tests` loaded | Available when Odoo is running |
| Browser smoke | Existing PowerShell headless fixture pattern under `addons/<module>/tests/browser/` | Available for module-owned fixtures |
| Clean install/update | Odoo `-i cw_custom_alerts` and `-u cw_custom_alerts` with `--stop-after-init` | Available when PostgreSQL is provisioned |

The development invocation in `Start_OD_Dev.ps1` uses database `OD_Dev`, port
8070, and the configured Odoo add-on path. Phase-01 disposable installation
should use a separate database and port, never the development database.

## Browser matrix and representative database

No organization-approved browser policy was found in the product, delivery,
or factory repositories. Observed local automation targets are Chrome
151.0.7922.172 at
`C:\Program Files\Google\Chrome\Application\chrome.exe` and Edge
152.0.4191.66 at
`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`.
Firefox is not installed. These observations are not a support-policy claim.

The product owner / release QA owner is assigned to record the supported
desktop browser matrix before the PH-06 browser acceptance gate. The Odoo
development-factory owner is assigned to provide the representative
nonproduction database lineage and provisioning requirements before upgrade
rehearsal. Until those external decisions are recorded, browser acceptance
and representative-database upgrade evidence remain open; this does not
prevent validation of the installable PH-01 boundary.

## Phase-01 verification notes

- Required dependencies are limited to `base_automation`, `web`, `bus`, and
  `mail`; no Enterprise or third-party runtime dependency is declared.
- Production and test asset bundles are explicit.
- The module-local Python contracts contain no Odoo imports. Release-sensitive
  automation and context adapters are named extension boundaries and are not
  implemented in this phase.
