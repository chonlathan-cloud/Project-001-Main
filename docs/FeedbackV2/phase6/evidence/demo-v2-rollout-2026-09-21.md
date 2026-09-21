# BOQ V2 demo rollout — 2026-09-21

Result: **PASS — BOQ V2 is enabled in demo only. Production beta was not
modified.**

All timestamps are UTC. The environment boundary was confirmed from the
repository environment inventory, live Cloud Run metadata, and the Business
Owner's explicit clarification:

| Environment | Frontend | Backend | Cloud SQL |
| --- | --- | --- | --- |
| Demo — changed in this rollout | `projects-001-fe` | `projects-001-be` | `project-001` |
| Production beta — untouched | `projects-001-fe-beta` | `projects-001-be-beta` | `project-001-beta` |

Excluded SaaS services/databases were not used.

## Authority and scope

The Business Owner approved all three demo-only actions:

1. add the missing frontend build-time BOQ V2 flag wiring;
2. deploy the demo frontend with `VITE_BOQ_V2_ENABLED=true`; and
3. create a demo backend revision with `BOQ_V2_ENABLED=true`.

The Owner also requested a durable record that can be used to reproduce the
same release in production beta after demo acceptance. No approval was granted
to migrate, configure, deploy, seed, or otherwise mutate production beta in
this action.

## Release identity

- Flag-wiring commit:
  `a404f29189d413d6aba232a19b09622e574c0fc3`
- Commit message: `support BOQ V2 frontend rollout flag`
- Existing compatible backend manifest digest:
  `sha256:3bad885791cf7a5d4f6db9148c7123f3b54045c84550a6a1ba3c1a56f54088ae`
- Backend Cloud Run platform digest:
  `sha256:57fcd0c5ef13d36f27c3df1750b71e1c766f99985437dec25ed41a4c1423eae2`
- New demo frontend image tag:
  `a404f29189d4-demo-boq-v2`
- New demo frontend manifest digest:
  `sha256:e8c0ee32f52b086daa1fe4cf9b7e44f3690904c160fad56d7f86df16167865ae`
- Frontend Cloud Run platform digest:
  `sha256:9767f1330a759aefde814fc48e5b818fbfee21233e93087c09ef5485ff921a79`

The frontend image carries OCI revision label
`a404f29189d413d6aba232a19b09622e574c0fc3`. Existing demo build configuration
was preserved, the API target remained `projects-001-be`, and only the BOQ V2
build flag changed. No Secret Manager payload was read. The build reused the
existing local public web configuration and preserved the deployed customer
LIFF identifier from the existing public bundle without printing it.

## Code change and validation

The frontend Dockerfile now declares and exports
`VITE_BOQ_V2_ENABLED=false` by default. `deploy_frontend.sh` passes the value
explicitly, and `cloudrun-frontend.build.env.example` documents the default.
The default therefore remains fail-closed for every future build unless the
release operator opts in.

Validation before image creation:

- frontend tests: 10 passed;
- frontend lint: passed;
- frontend production build with `VITE_BOQ_V2_ENABLED=true`: passed;
- generated feature bundle evaluated the enabled value as true;
- `bash -n deploy_frontend.sh`: passed;
- `shellcheck`: not run because the executable is not installed;
- existing Vite chunk-size warning remained;
- Docker npm audit reported the existing 10 findings (4 moderate, 6 high);
  no automatic dependency mutation was performed.

## Demo deployment

| Component | Previous revision | New revision | Change | Final traffic |
| --- | --- | --- | --- | ---: |
| Backend | `projects-001-be-00132-tjj` | `projects-001-be-00133-mwt` | Add `BOQ_V2_ENABLED=true`; image unchanged | 100% |
| Frontend | `projects-001-fe-00061-4bl` | `projects-001-fe-00062-l9k` | Exact new image digest with V2-enabled bundle | 100% |

Backend readiness completed at `2026-09-21T15:13:17.808040Z`; frontend
readiness completed at `2026-09-21T15:13:52.478643Z`.

The canonical backend revision spec matched its predecessor after removing the
image and the single new flag. The canonical frontend runtime spec matched its
predecessor after removing only the image. Service accounts, runtime resources,
secrets, environment variables, Cloud SQL attachments, ingress, scaling, and
traffic policy were otherwise preserved. No IAM change was made.

## Demo project and application validation

The Owner-authorized browser workflow created:

- project: `Renovation The Mall`
- UUID: `57cbf401-4870-4a13-b548-96445dc1c8f5`
- type/status: `COMMERCIAL` / `ACTIVE`

Database preflight confirmed migration revision `20260917_0003` and zero
budget-source rows. Post-rollout validation confirmed:

- backend health: 200;
- unauthenticated V2 workspace: 401, proving the feature gate passed and the
  authentication boundary remained active;
- frontend root: 200;
- deployed feature bundle: V2 enabled;
- authenticated Projects UI: all Native BOQ buttons enabled;
- authenticated navigation to the new project workspace: passed;
- empty-state page displayed `Create blank draft`;
- no draft was created and all 22 V2 tables remained empty;
- no active project budget source was created;
- bounded logs for the new revisions contained 26 backend 200s, one expected
  backend 401, and 35 frontend 200s;
- bounded error query returned no HTTP 5xx or severity-ERROR entry.

The browser was left at the empty Native BOQ workspace so the Owner can create
the first synthetic draft manually.

## Production-beta parity packet — not authorized or executed

When demo acceptance is complete, production beta must be treated as a new
controlled release. Do not replay demo data and do not infer approval from this
document.

1. Obtain separate Business Owner approval for production-beta backup,
   migration, backend flag, frontend deployment, controlled UAT data, and any
   later source activation/cutover.
2. Reconfirm target identity exactly:
   `projects-001-be-beta`, `projects-001-fe-beta`, and `project-001-beta`.
3. Capture beta revision/digest/config/traffic baselines and a fresh retained
   Cloud SQL backup; run an isolated restore rehearsal if the beta schema
   differs from the already-proved profile.
4. Run the fail-closed beta schema preflight. Stamp only an approved matching
   legacy schema, then apply additive revisions through `20260917_0003`; never
   copy demo rows or seed data into beta.
5. Backend parity candidate: use the reviewed backend digest recorded above or
   rebuild it from a separately recorded clean release SHA; add
   `BOQ_V2_ENABLED=true` only after the beta schema gate passes.
6. Rebuild the frontend from commit `a404f29189d413d6aba232a19b09622e574c0fc3`
   with the beta API URL, beta Identity Platform tenant, beta public web
   configuration, and `VITE_BOQ_V2_ENABLED=true`. The demo frontend image must
   not be reused because its API/auth configuration is demo-specific.
7. Deploy exact immutable digests with zero/canary traffic where applicable,
   verify configuration preservation, then shift traffic only after health,
   authentication, feature-gate, and bounded-log checks pass.
8. Create a controlled beta UAT project only with explicit data-write approval.
   Exercise create/save/reload, hierarchy, issue/accept/revise/alternative/CO,
   vendor-cost publication, Price Database, exports, permissions, and financial
   read compatibility before any source activation.
9. Record candidate baseline/source versions and require separate Owner
   cutover approval. Enabling the UI is not budget-source activation.

Demo rollback points are backend `projects-001-be-00132-tjj` and frontend
`projects-001-fe-00061-4bl`. A demo rollback would disable the backend flag and
route the frontend to its preceding revision; no schema downgrade is required.

## Preserved environment drift

The demo backend reports `APP_ENV=production` even though repository ownership
documents classify `projects-001-*` and `project-001` as demo. Its Cloud Run
attachment also retains the pre-existing excluded SaaS connection alongside
the demo connection, although the observed application data is in
`project-001`. Neither drift was changed in this focused rollout. Do not copy
either setting into production beta; beta retains its independent
`APP_ENV=prod-beta`, secret, tenant, database, storage, and service boundaries.
