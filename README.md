# SwiftHub: Dark-Store Inventory & 10-Minute Dispatch Engine

**Live Application:** https://swifthub-rho.vercel.app/

SwiftHub is a full-stack hyperlocal quick-commerce dark-store inventory and 10-minute dispatch engine featuring JWT role-based access control (Customer vs. Branch Admin), strict branch-level tenant isolation across two Bangalore dark-store hubs (**HSR Layout Hub** and **Koramangala Hub**), real-time WebSocket synchronization, and machine-learning SLA prediction.

> **Non-Commercial Disclaimer:** SwiftHub is a non-commercial technical portfolio project using simulated operational data, synthetic historical orders, and simulated rider telemetry.
>
> **Note on Live Demo Hosting:** The backend runs on Render's free tier, so the first request after a period of inactivity may take ~30–50 seconds to wake up.

---

## Live Demo Access

Use the pre-configured demo accounts below to test both the Customer Storefront and the isolated Branch Admin consoles on [https://swifthub-rho.vercel.app/](https://swifthub-rho.vercel.app/).

| Role | Assigned Hub | Email | Password |
| :--- | :--- | :--- | :--- |
| Customer | Any (Browse Both) | `aarav.demo@gmail.com` | `Customer123!` |
| Customer | Any (Browse Both) | `priya.demo@gmail.com` | `Customer123!` |
| Branch Admin | HSR Layout Hub | `hsr.admin@swifthub.com` | `AdminHSR123!` |
| Branch Admin | Koramangala Hub | `koramangala.admin@swifthub.com` | `AdminKora123!` |

**Recommended Evaluation Flow:**
1. Sign in as a **Customer** (`aarav.demo@gmail.com`) in one browser window, select **HSR Layout Hub**, and place an order.
2. Sign in as the **HSR Layout Hub Admin** (`hsr.admin@swifthub.com`) in an incognito window to see the live incoming order, pick/pack items, dispatch a rider, and view branch-isolated analytics.
3. Sign in as the **Koramangala Hub Admin** (`koramangala.admin@swifthub.com`) to verify strict tenant isolation—HSR Layout orders, inventory, and riders are not visible or accessible from this account.

---

## Tech Stack & Infrastructure

| Layer | Technologies Used | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Vue 3 (`<script setup>`), Vite, Pinia, Tailwind CSS, Lucide Vue Next | Reactive SPA, role-based views, modular state stores, responsive UI |
| **Maps & Visualization** | Leaflet.js (OpenStreetMap), Chart.js | Live hub/drop-off/rider GPS maps and real-time SLA & latency charts |
| **Backend & Real-Time** | Python 3.12, FastAPI, Uvicorn, WebSockets, Pydantic v2 | Async REST API, strict contract validation, bi-directional live sync |
| **Data & Persistence** | SQLAlchemy ORM, SQLite (WAL mode), PostgreSQL-ready (`DATABASE_URL`) | Relational modeling, atomic inventory locking, append-only audit trail |
| **Auth & Security** | HS256 JWT, PBKDF2-SHA256 Password Hashing, Role/Tenant Middleware | Customer vs. Branch Admin RBAC and strict per-branch isolation |
| **Machine Learning** | Scikit-learn (`GradientBoostingRegressor`, `RandomForestClassifier`), Pandas, Joblib | Sub-millisecond ETA regression and 10-minute SLA breach risk scoring |
| **Containerization & Cloud** | **Docker**, **Docker Compose**, **Render (Docker)**, **Vercel** | Reproducible containerized backend builds, one-command local stack, cloud hosting |
| **Testing & QA** | Pytest, FastAPI TestClient, Vitest, jsdom | Automated RBAC, tenant isolation, concurrency, state machine, ML & UI store tests |

---

## Core Functionalities

### 1. Customer Storefront & Live Order Tracking
- **Two-Hub Browsing & 18-Product Catalog:** Browse live inventory across **HSR Layout Hub** and **Koramangala Hub** with category filtering, keyword search, local product photography, INR pricing, and clean conditional availability indicators (`Low Stock` when under 5 units, `Out of Stock` when depleted).
- **Express Cart & Atomic Checkout:** Slide-over cart drawer with real-time quantity caps and transactional stock reservation. If concurrent buyers compete for the final unit of an item, the conflict is caught cleanly and surfaced with an `HTTP 409 Conflict` message.
- **Personal Live Order Tracker:** Authenticated customers can view **My Orders** with a 5-step progress timeline, live 10-minute SLA countdown clock, ML-predicted ETA and SLA risk indicator, pre-dispatch self-cancellation, and an interactive OpenStreetMap Leaflet map showing the dark-store hub, drop-off pin, and live rider location.

### 2. Authentication & Branch-Level Tenant Isolation
- **Role-Based Access Control (RBAC):** Email and password authentication powered by salted PBKDF2-SHA256 password hashing and signed HS256 JWT bearer tokens, separating **Customer** and **Branch Admin** workflows.
- **Strict Per-Branch Isolation:** Every operational endpoint automatically scopes queries to the signed-in Branch Admin's assigned hub. Cross-branch inspection, restocking, order advancement, rider access, analytics, or simulation triggers are immediately rejected with `HTTP 403 Forbidden`.
- **Customer Data Scoping:** Customers can only view or cancel orders belonging to their own account.

### 3. Dark-Store Ops Console (Branch Admin Only)
- **SLA-Prioritized Order Queue:** Incoming orders are automatically ranked by highest ML SLA breach risk and shortest remaining 10-minute delivery window.
- **Aisle-Sorted Picking Workflow:** Displays internal SKU codes and aisle locations exclusively to pickers and branch admins, paired with a backend-enforced order state machine (`Order Placed` -> `Picking` -> `Packed` -> `Out for Delivery` -> `Delivered`).
- **Low-Stock Replenishment:** Dedicated alert panel surfaces items at or below their reorder threshold with one-click `+10` restocking synced immediately over WebSockets.

### 4. Rider Dispatch & Live Lifecycle Simulator (Branch Admin Only)
- **Nearest-Rider Auto-Assignment:** When an order is marked packed, the dispatch engine calculates Haversine distances to all idle riders stationed at that hub and automatically assigns the nearest available rider.
- **Live Fleet Telemetry:** Real-time hub rider roster (`IDLE`, `ASSIGNED`, `DELIVERING`) paired with a keyless OpenStreetMap fleet map.
- **One-Click Live Demo Simulation:** Triggers a real end-to-end order inside the admin's assigned hub and animates picking, packing, nearest-rider dispatch, smooth GPS movement along the delivery route, and doorstep completion over ~35 seconds.

### 5. Operations Analytics Dashboard (Branch Admin Only)
- **Event-Driven KPIs & Charts:** Chart.js visualizations computed directly from each hub's append-only order lifecycle audit trail, measuring 10-minute SLA compliance, average picking duration, dispatch wait time, last-mile delivery latency, and unit volume by product category.

---

## Concurrency & Inventory Safety

To prevent overselling when multiple shoppers check out scarce items simultaneously:
1. **Deterministic Lock Ordering:** Cart items are aggregated and processed in a consistent sorted order inside each transaction to eliminate lock-order deadlocks.
2. **Conditional Atomic Reservation:** Inventory is only decremented and moved to reserved stock when sufficient available quantity is confirmed in a single atomic database operation.
3. **Automatic Conflict Rollback:** If any item lacks sufficient stock at commit time, the entire transaction rolls back and returns `HTTP 409 Conflict` with the affected item details.
4. **Atomic Cancellation Restoration:** Cancelling an order prior to dispatch atomically returns reserved units back to available stock within the same transaction that records the cancellation event.

---

## Machine-Learning ETA & SLA Risk Engine

The ML pipeline (`backend/ml/`) trains on 2,500 synthetic Bangalore dark-store orders modeling peak-hour traffic, picker aisle traversal, hub queue congestion, and rider availability using six operational signals:
- Total item count in the order
- Number of distinct dark-store aisles required for picking
- Current active order queue depth at the hub
- Count of idle riders available at the hub
- Haversine distance from the dark store to the customer drop-off location
- Order hour of day to capture morning and evening congestion

Two serialized Scikit-learn models are loaded once at backend startup for sub-millisecond inference on every checkout:
- **ETA Predictor (`GradientBoostingRegressor`):** Estimates total fulfillment duration in seconds (test MAE ~27s, R2 ~0.95).
- **SLA Breach Classifier (`RandomForestClassifier`):** Predicts the probability of exceeding the 10-minute (600-second) SLA target (test ROC-AUC ~0.976).

---

## Project Structure

```text
swifthub/
├── backend/
│   ├── Dockerfile                 # Python 3.12-slim container image for Render & Docker Compose
│   ├── app/
│   │   ├── main.py                # FastAPI REST routes, RBAC enforcement, CORS, WebSocket endpoint
│   │   ├── auth.py                # Salted PBKDF2 password hashing, HS256 JWT tokens, role guards
│   │   ├── models.py              # Relational domain models for hubs, catalog, stock, users, riders & audit trail
│   │   ├── schemas.py             # Pydantic v2 request/response contracts
│   │   ├── seed.py                # Idempotent 2-hub, 4-demo-user, 18-product, and history seeder
│   │   ├── ws.py                  # WebSocket connection manager for live broadcasts
│   │   └── services/
│   │       ├── inventory.py       # Atomic conditional stock reservation, restocking & restoration
│   │       ├── state_machine.py   # Strict order lifecycle transitions & audit trail recording
│   │       ├── ml_inference.py    # Startup-loaded Scikit-learn ETA & SLA risk inference
│   │       ├── dispatch.py        # Haversine nearest-rider auto-assignment
│   │       └── simulator.py       # ~35s end-to-end lifecycle & GPS movement simulator
│   ├── ml/
│   │   ├── generate_dataset.py    # Synthetic dark-store order dataset generator
│   │   ├── train_models.py        # Model training & evaluation pipeline
│   │   └── artifacts/             # Serialized ETA & SLA models plus evaluation metrics
│   └── tests/                     # Pytest suite (RBAC, tenant isolation, concurrency, state machine, ML)
├── frontend/
│   ├── Dockerfile                 # Node container image for local Docker Compose builds
│   ├── vercel.json                # Vercel Vite build & SPA rewrite configuration
│   ├── public/assets/products/    # Local product photography for all 18 catalog items
│   └── src/
│       ├── api/client.js          # Authenticated REST client (VITE_API_URL)
│       ├── composables/           # Auto-reconnecting WebSocket sync composable
│       ├── stores/                # Pinia state stores (auth, hub operations, cart)
│       ├── components/            # Storefront, AuthModal, CartDrawer, LiveOrderTracker, LiveDispatchMap, OpsConsole, LowStockPanel, RiderDispatchPanel, AnalyticsDashboard
│       └── tests/                 # Vitest unit tests
├── docker-compose.yml             # Multi-container orchestration for local backend + frontend
└── render.yaml                    # Render Infrastructure-as-Code deployment blueprint
```

---

## Local Setup

### Option 1: Docker Compose
```bash
docker compose up --build
```
- Frontend: `http://localhost:5173`
- Backend API & Swagger Docs: `http://localhost:8000/docs`

### Option 2: Manual Local Run

**Backend:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Running Tests
```bash
# Backend Pytest suite (RBAC, branch isolation, state machine, ML inference, concurrency)
cd backend && .venv/bin/pytest -v

# Frontend Vitest suite (cart state & SLA utilities)
cd frontend && npm test
```

---

## Production Deployment (Render + Vercel)

- **Frontend (Vercel):** Deployed at [https://swifthub-rho.vercel.app/](https://swifthub-rho.vercel.app/) from Root Directory `frontend` using `frontend/vercel.json`, with `VITE_API_URL` pointing to the Render backend (WebSocket `wss://` is derived automatically).
- **Backend (Render):** Deployed from Root Directory `backend` with health check `/api/health`, `JWT_SECRET_KEY`, and `FRONTEND_URL=https://swifthub-rho.vercel.app`.
