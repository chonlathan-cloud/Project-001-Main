# Repository Guidelines

## Project Structure & Module Organization

This repository is split into a React frontend and FastAPI backend:

- `Projects-001-FE/`: React + Vite app. Source lives in `src/`, reusable UI in `src/components/`, static assets in `src/assets/` and `public/`.
- `Projects-001-BE/`: FastAPI service. API routers are in `app/api/v1/`, models in `app/models/`, schemas in `app/schemas/`, and business logic in `app/services/`.
- `docs/`: product, architecture, API/DB, implementation, backlog, and user manuals.
- `Design/`: flow/design documentation and design concept prototype.
- Root deploy helpers include `deploy_frontend.sh`, `deploy_backend.sh`, and Cloud Run env examples.

@ui-ux-engineer
You are an expert UI/UX Engineer, Frontend Architect, and Design Systems specialist.
Your primary responsibility is to translate design specifications, tokens, and wireframes into production-ready React components using Tailwind/CSS.

Context Boundary
- **Allowed Directories:** `Projects-001-FE/` and `Design/`
- **Disallowed Directories:** `Projects-001-BE/` (Do not modify backend logic)

Tools
- mcp: google-stitch

Instructions
1. Always query the `google-stitch` MCP server to fetch the latest design tokens and UI layouts before writing code.
2. Implement components in `Projects-001-FE/src/components/`.
3. Ensure responsiveness and maintain strict adherence to the design system.
4. Do not alter business logic or API data fetching layers without explicit permission.

Frontend:

```bash
cd Projects-001-FE
npm install
npm run dev      # start Vite dev server
npm run build    # production build
npm run lint     # ESLint checks
npm run preview  # preview built app
```

Backend:

```bash
cd Projects-001-BE
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

For local configuration, copy from `.env.example` files instead of hardcoding secrets.

## Coding Style & Naming Conventions

Use JavaScript/JSX ES modules in the frontend and Python 3 async patterns in the backend. Keep React page components in `PascalCase` files such as `InputPage.jsx`; utility modules use lower camel case exports from files like `api.js` and `auth.js`. Backend routers and services use snake_case filenames and functions. Follow existing formatting: two-space indentation in JSX/JS and four-space indentation in Python. Run `npm run lint` before frontend changes.

## Testing Guidelines

No automated test suite is currently checked in. When adding tests, colocate frontend tests near the relevant component or add a clear `tests/` folder, and use descriptive names such as `InputPage.test.jsx`. Backend tests should target routers/services with `pytest` naming, for example `tests/test_input_requests.py`. Until tests exist, verify with lint, local app startup, and focused manual flows.

## Commit & Pull Request Guidelines

Recent history uses short imperative commit summaries, for example `add profile and barch data` and `Remove service account key and update gitignore`. Keep commits small and action-oriented. PRs should include a brief summary, changed areas (`FE`, `BE`, `docs`, `deploy`), verification steps, linked issues if any, and screenshots for visible UI changes.

## Security & Configuration Tips

Never commit service account keys, `.env` files, or real secrets. Use the provided env examples and Google Secret Manager/Cloud Run env files for deployment. GCS assets such as KYC, receipts, and profile images are private and should only be exposed through signed URLs.
