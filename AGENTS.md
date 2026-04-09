# Repository Guidelines

## Project Structure & Module Organization
This repository is split into two apps. `frontend/` contains the Vite + React + TypeScript UI; keep reusable UI in `frontend/src/components`, pages in `frontend/src/pages`, API calls in `frontend/src/services`, and shared types in `frontend/src/types`. `backend/` contains the FastAPI service; endpoints live in `backend/api`, comparison and Excel logic in `backend/services`, configuration in `backend/config`, exports in `backend/outputs`, and tests in `backend/tests`. Deployment files live at the repo root in `docker-compose.yml`, with app-specific Dockerfiles under each app.

## Build, Test, and Development Commands
Run commands from the relevant app directory.

- `cd frontend; npm install` installs UI dependencies.
- `cd frontend; npm run dev` starts the Vite dev server on `http://localhost:5173`.
- `cd frontend; npm run build` runs TypeScript compilation and creates `frontend/dist/`.
- `cd frontend; npm run lint` checks the frontend with ESLint.
- `cd backend; python -m venv venv; .\venv\Scripts\Activate.ps1; pip install -r requirements.txt` prepares the API environment.
- `cd backend; python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000` starts the backend on `http://localhost:8000`.
- `docker-compose up --build` runs both services together.

## Coding Style & Naming Conventions
Follow existing style before introducing new patterns. Frontend code uses 2-space indentation, TypeScript, functional React components, PascalCase file names (`FileUpload.tsx`, `OrderComparison.tsx`), and camelCase for variables/functions. Backend code should follow PEP 8 with 4-space indentation, snake_case functions, and small service modules. Keep boundaries explicit: parsing in `excel_parser.py`, comparison logic in `data_comparator.py`, API wiring in `api/compare.py`.

## Testing Guidelines
Backend tests use `pytest` and belong in `backend/tests` with names like `test_compare_api.py`. Run them with `cd backend; pytest`. Add or update tests whenever API behavior, parsing rules, or comparison logic changes. The frontend currently has no committed test runner, so validate changes with `npm run lint` and `npm run build` before opening a PR.

## Commit & Pull Request Guidelines
Recent history uses Conventional Commits such as `feat: ...` and `fix: ...`; keep that format and write imperative summaries. PRs should include a short problem/solution description, linked issue if applicable, test evidence (`pytest`, `npm run lint`, `npm run build`), and screenshots for UI changes. Keep changes scoped.

## Environment & Configuration Tips
Use Node `v24.9.0` and Python `3.12.10` to match the current workspace. Keep machine-specific secrets out of git. Frontend API requests assume `VITE_API_URL`; Docker Compose maps the frontend to port `80` and the backend to `8000`.
