# CivicPulse AI — From Complaints to Action

**Every Complaint Matters. Every Action Counts.** CivicPulse AI is a civic complaint prototype that connects citizen reporting, transparent rules-based analysis, location insights, administrative review, and complaint tracking.

## Capture → Understand → Reveal → Act

- **Capture:** citizens submit a title, description, category (optional), locality, optional coordinates, affected transportation mode, and an optional image. Coordinates are validated and never fabricated. Images are type-checked, capped at 5 MB, previewed before submission, and stored as files outside SQLite. Categories include roads/infrastructure, water supply, sanitation, drainage/waterlogging, street lighting, electrical/public safety, transportation, animal control, and other. Transportation mode is optional and supports the requested walking, bicycle, two-wheeler, car, auto-rickshaw, bus, truck, general traffic, not-applicable, and other choices.
- **Understand:** the backend suggests a category, creates a concise summary from submitted facts, checks likely duplicates, and records a priority score with five structured factors and a plain-language explanation. Explicit user categories remain intact alongside the suggested category.
- **Reveal:** the admin dashboard shows database-backed totals, category/priority/status/time/locality charts, transportation-mode analytics, actual coordinate markers, and deterministic hotspot groups. Search plus category, priority, status, transportation mode, locality text, and date range filters update the complaint list, map, and analytics.
- **Act:** admins review duplicate candidates, assign a team, advance only valid status transitions, and record resolution/rejection notes. The priority queue links to an issue intelligence page with evidence, factor explanations, related reports, status history, map directions, and an explicitly heuristic resource plan. Persistent work orders are linked to complaints and support planned, in-progress, completed, and cancelled states. Action briefs and the rule-based CivicPulse Assistant use current database records. Citizens can track a complaint ID and status history.

## Technology and structure

React, TypeScript, Vite, Tailwind CSS, React Router, Recharts, Leaflet/OpenStreetMap, Lucide React; Python, FastAPI, Pydantic, SQLAlchemy, SQLite, pytest.

```text
backend/app/main.py                   API, safe additive schema initialization
backend/app/models.py                 complaint and status history models
backend/app/services/                 analysis, scoring, duplicates, hotspots, briefs, chatbot, uploads
backend/app/main.py                   additive work-order endpoints and resource plans
backend/scripts/seed_data.py          idempotent 45-report fictional dataset
backend/scripts/seed_hackathon_demo.py stable-ID 20-report synthetic Mangaluru set
backend/tests/                        isolated API/service tests
frontend/src/App.tsx                  citizen flows, admin dashboard, map, assistant, routes
frontend/src/Operations.tsx           priority queue, issue intelligence, work-order planner
frontend/src/api.ts                   frontend API, uploads, work-order service layer
frontend/src/errors.ts                readable API/network/validation error formatter
frontend/src/index.css                responsive UI and Tailwind integration
```

## Windows PowerShell setup

Use separate terminals. From the project root, start the backend:

```powershell
cd C:\Users\ADMIN\Desktop\civicpulse-ai\backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe scripts\seed_data.py
.\.venv\Scripts\python.exe scripts\seed_hackathon_demo.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8010
```

The API runs at `http://127.0.0.1:8010`; API docs are at `/docs`. SQLite is created at `backend/data/civicpulse.db`. Startup adds any missing nullable analysis columns, creates the `work_orders` and `duplicate_reviews` tables if absent, and backfills structured rule-based analysis; it does not drop tables or delete complaints. `seed_data.py` inserts 45 fictional `CIV-DEMO-...` records; `seed_hackathon_demo.py` adds 20 stable-ID `CIV-HACK-...` synthetic records in a Mangaluru demo geography. Both skip IDs already present. The reports, coordinates, and workflow histories are demonstration data, not verified citizen incidents.

In a second PowerShell terminal:

```powershell
cd C:\Users\ADMIN\Desktop\civicpulse-ai\frontend
npm.cmd install
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
npm.cmd run dev
```

Open `http://localhost:5173`. `frontend/.env.example` configures `VITE_API_URL=http://127.0.0.1:8010/api`; update `frontend/.env` if the backend uses another address. The production build command is `npm.cmd run build`.

Backend tests:

```powershell
cd C:\Users\ADMIN\Desktop\civicpulse-ai\backend
.\.venv\Scripts\python.exe -m pytest -v
```

## Analysis rules

All analysis and chat responses are deterministic rules-based prototype logic; no LLM or trained model is used. Category and summary suggestions are based only on the submitted title, description, and locality. The summary does not add unsubmitted incident facts.

Priority uses one shared service and these prototype factors:

| Factor | Maximum | Evidence examples |
|---|---:|---|
| Safety Risk | 30 | Exposed wires, hazards, accidents, road/pedestrian obstructions |
| Severity | 25 | Serious failures, leaks, damaged assets, or conservative baseline |
| Public Impact | 20 | Shared services/places, neighborhood impact, or unknown reach |
| Recurrence | 15 | Up to three 5-point increments from matching existing reports |
| Time Sensitivity | 10 | Explicit urgency, ongoing issue, or conservative default |

The five stored factor scores sum to the final 0–100 score. Labels are Low 0–24, Medium 25–49, High 50–74, and Critical 75–100. Relevant pedestrian, bicycle, or two-wheeler context can affect safety scoring when the complaint is about roads/footpaths; merely selecting a mode does not raise the score. Reasons distinguish inference from measured evidence and state that human review is required. These are not official municipal standards.

Duplicate candidates use normalized word-token Jaccard similarity (threshold 0.25), same canonical category (legacy names are grouped with their expanded labels), locality/transport context, and a 500 m safeguard when both coordinates are present. Submissions remain separate. The first candidate is linked as the primary report; its direct duplicate count increments once. No-coordinate matches are text/locality based, without invented map positions.

Hotspots use deterministic greedy grouping: reports within 1,000 m of a cluster anchor, at least two located reports per group. The response includes actual IDs, mean coordinates, category counts, average priority, transportation modes, and a suggested review action. Reports without coordinates remain in locality analytics but are not plotted.

## Priority queue, resource plans, and work orders

The Priority-Based Reports page reads saved backend reports and sorts active work first by Critical/High/Medium/Low, then descending score, then oldest submission, then complaint ID for a stable tie. Filters include search, priority, category, status, transportation mode, locality, and an explicit option to include resolved/rejected records. The page loads up to the latest 100 reports in one request.

Issue Intelligence shows the stored report, uploaded evidence (or an explicit no-image message), persisted score factors, related candidates, status history, and supplied coordinates. The map navigation link sends the exact saved coordinates when they exist. A transportation mode selected by the citizen is identified as reported; broader impact is not asserted without evidence.

The resource plan is a deterministic category-based starting estimate, currently defaulting to a small inspection crew and short duration. It does not estimate repair materials, site complexity, or staff availability from verified field data. The API marks it LOW confidence and returns assumptions. Treat it as an illustrative planning aid and confirm needs on site.

Work orders are stored in the additive `work_orders` table and linked to existing report rows. Their lifecycle is PLANNED → IN_PROGRESS → COMPLETED, with CANCELLED available; invalid state changes are rejected. Estimates, assigned team, materials, and notes can be edited. Team workload on the planner is calculated only from recorded, active work orders with a team name; no department roster or capacity model is configured. Work-order status records planning progress and do not prove the physical work was performed.

Possible duplicate candidates can be explicitly confirmed or dismissed from the issue page. Decisions are recorded in the additive `duplicate_reviews` table; reports remain separate, and the decision does not merge or delete either submission. Duplicate matching remains the documented text/category/location heuristic rather than a verified identification of the same incident.

## Assistant, action briefs, and routes

The **CivicPulse Assistant** is a read-only, rule-based chat endpoint (`POST /api/chat`). It supports complaint-ID tracking and stored priority explanations, open/critical counts, categories, transportation modes, localities, hotspots, duplicate summaries, and data-backed briefs. It cannot assign or resolve complaints.

Action briefs are built from real saved reports and include a location/category group, report IDs, priority distribution, transportation modes, safety-risk references, evidence summaries, and proposed human review steps. They do not represent a completed inspection or repair.

Other useful endpoints include `POST /api/reports`, `GET /api/reports`, `GET /api/reports/{id}`, `GET /api/reports/{id}/history`, `GET /api/reports/{id}/duplicates`, `GET/POST /api/reports/{id}/duplicate-review(s)`, `GET /api/reports/{id}/resource-plan`, `GET /api/analytics/summary`, `GET /api/analytics/hotspots`, `POST /api/uploads`, `GET/POST /api/admin/work-orders`, `PATCH /api/admin/work-orders/{id}`, and admin assignment/status endpoints under `/api/admin/reports/...`.

## Five-minute demo

1. Submit “Deep pothole near school entrance,” choose **Roads**, use the fictional **School Road** locality and approximate demo coordinates `12.9716, 77.5946`, and select **Two-Wheeler / Motorcycle**. Note the complaint ID.
2. Open the complaint details to show the suggested category, summary, duplicate candidates, priority factor breakdown, score, explanation, and transportation inference.
3. In Admin, find its marker, inspect a nearby hotspot, and view the transportation and priority charts.
4. Ask the Assistant “Why was CIV-… given this priority?” and “Which transportation modes are most affected by open complaints?”
5. Assign a team, move the complaint through Under Review → Assigned → In Progress, and track the persisted status/history. Explain that this demo state is not proof of real-world repair.

## Limitations and safety

- No authentication or role-based access is implemented; complaint IDs are not secure credentials and admin APIs are unauthenticated. Do not use this prototype for sensitive production records.
- OpenStreetMap tiles require network access. If tiles fail, the map displays a warning and the rest of the admin dashboard remains usable.
- The score, duplicate candidates, categories, summaries, hotspot boundaries, and chat are rules-based and can be wrong. They require human review.
- Image upload stores validated files locally in `backend/data/uploads`; no image analysis is claimed. Configure durable, access-controlled storage before hosting.
- No real municipal integration, notifications, geocoding, or proof of field work exists. Database status changes are workflow records only.
- Administrative, duplicate-review, and work-order endpoints remain unauthenticated. Do not expose them to the public internet without adding access controls. Duplicate-review records are administrative judgments, not ground truth.
- Headless Chrome checks covered the live admin dashboard, API error and Retry recovery, empty search results, priority sorting/filtering, report details and missing-image notice, map marker/hotspot rendering, and the empty work-order state. The priority page was checked at desktop and 390 px mobile widths with no horizontal overflow. This is not a complete browser end-to-end suite; image upload, map interaction, work-order edits, and citizen submission/tracking flows were not browser-tested.
- SQLite files on ephemeral hosting may not persist. Use persistent storage or a managed database for deployment, configure `DATABASE_URL`, `CORS_ORIGINS`, and `VITE_API_URL`, and protect the API before exposing it publicly.
