# Public Customer Report Links

## Decision

Customer report viewing no longer requires customer registration, LINE Login, or an access-request approval. Admin/Owner review and publication approval remain unchanged.

Anyone holding a project's active share link can view that project's latest published Daily Reports. The link is a bearer capability and may be forwarded, so operators can rotate or disable it immediately.

## Access model

- One stable share capability per project.
- HMAC-signed token containing the project ID, environment, tenant, and revocation version.
- No raw token is stored in Firestore.
- Rotation increments the stored version and invalidates every previous copy.
- Disabling a link also invalidates previous copies.
- Public responses expose only published customer-facing fields and curated media metadata.
- Signed GCS media URLs retain the existing short expiry.
- Anonymous acknowledgement and question creation are not exposed.

The browser link uses a URL fragment:

```text
https://frontend.example/shared/project-reports#access={TOKEN}&report={REPORT_ID}
```

Fragments are not included in the initial HTTP request or normal referrer headers. The React page sends the token to the API in the `X-Customer-Report-Share` header.

## API contract

Admin/Owner project controls:

```text
GET /api/v1/daily-reports/projects/{project_id}/share-link
PUT /api/v1/daily-reports/projects/{project_id}/share-link
```

The update body is:

```json
{
  "enabled": true,
  "rotate": false
}
```

Anonymous read-only routes:

```text
GET /api/v1/daily-reports/public/reports
GET /api/v1/daily-reports/public/reports/{report_id}
GET /api/v1/daily-reports/public/media/{media_id}/signed-url
```

All anonymous routes require `X-Customer-Report-Share` and are rate limited.

## Rollout

1. Deploy backend and frontend with `CUSTOMER_REPORT_PUBLIC_SHARE_ENABLED=false`.
2. Create `CUSTOMER_REPORT_SHARE_SECRET` in Secret Manager. If omitted, the backend uses `JWT_SECRET_KEY` with a separate token purpose during migration.
3. Add the secret mapping to `BACKEND_SECRET_ENV_VARS`.
4. Enable or prepare links from the Daily Report review workspace.
5. Set `CUSTOMER_REPORT_PUBLIC_SHARE_ENABLED=true` and deploy the backend.
6. Publish a beta report and confirm the LINE Flex button opens `/shared/project-reports` without login.
7. Confirm unpublished reports, cross-project report IDs, old rotated links, and disabled links return `404`.
8. After the beta period, remove the legacy authenticated customer portal and customer approval UI in a separate cleanup release.

## Operational rule

Rotate the link when a customer leaves the project group, the link is posted outside the intended group, or the project changes ownership. Disable it when the project is completed or report access should end.
