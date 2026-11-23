# SwiftHub: Dark-Store Inventory & 10-Minute Dispatch Engine

SwiftHub is a full-stack hyperlocal quick-commerce dark-store inventory and 10-minute dispatch engine inspired by real-world 10-minute delivery hubs in Bangalore (Koramangala Hub, Indiranagar Hub, and HSR Layout Hub).

> **Non-Commercial Disclaimer:** SwiftHub is a non-commercial technical portfolio project using simulated operational data, synthetic historical orders, and simulated rider telemetry.

---

## Key Capabilities

1. **Customer Storefront & Live Order Tracker**
   - Multi-hub selector across Bangalore dark stores with live WebSocket-synced stock counts, aisle tags (`A1-Dairy` through `A6-Pantry`), and low-stock badges.
   - Slide-over cart drawer with atomic checkout reservation and clear conflict messaging (`HTTP 409 Conflict`) when concurrent buyers compete for the last unit.
   - Live 5-step order timeline, 10-minute SLA countdown clock, ML-predicted ETA & SLA breach risk badge, and interactive Leaflet.js map tracking the dark-store hub, customer drop-off pin, and moving rider marker.
2. **Dark-Store Ops Console (Picker & Hub Manager)**
   - Live incoming order queue automatically sorted by highest ML SLA breach risk and lowest remaining SLA time.
   - Aisle-sorted interactive pick list per order with strict backend-enforced status advancement (`Start Picking` -> `Mark Packed` -> `Dispatch Rider` -> `Mark Delivered`).
   - Low-stock reorder alert sidebar highlighting SKUs at or below `reorder_threshold` with one-click `Restock (+10)` replenishment.
3. **Rider Dispatch Panel & Live Demo Simulator**
   - Live hub rider roster (`IDLE`, `ASSIGNED`, `DELIVERING`), assigned orders, and fleet-wide Leaflet map.
   - One-click **Run Live Demo Simulation** (`POST /api/simulation/trigger`) that places a real order and animates the complete picking, nearest-rider auto-assignment, and GPS delivery lifecycle over ~35 seconds.
4. **Operations Analytics Dashboard**
   - Chart.js visualizations computed directly from the append-only `order_events` audit table: 10-minute SLA compliance rate, average picking vs. dispatch wait vs. delivery latency, and order volume by category.

---

## Architecture & Tech Stack

```text
swifthub/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI routes, CORS, WebSocket endpoint, lifespan
│   │   ├── models.py              # SQLAlchemy ORM schema (stores, products, inventory, orders, riders, order_events)
│   │   ├── schemas.py             # Pydantic v2 request/response contracts
│   │   ├── seed.py                # Idempotent Bangalore dark-store, SKU, rider, and history seeder
│   │   ├── ws.py                  # WebSocket ConnectionManager for live broadcasts
│   │   └── services/
│   │       ├── inventory.py       # Atomic conditional UPDATE locking & stock restoration
│   │       ├── state_machine.py   # Strict order status transitions & audit logging
│   │       ├── ml_inference.py    # Startup-loaded Scikit-learn ETA & SLA risk predictor
│   │       ├── dispatch.py        # Haversine nearest-IDLE-rider auto-assignment
│   │       └── simulator.py       # ~35s background lifecycle and GPS movement simulator
│   ├── ml/
│   │   ├── generate_dataset.py    # 2,500-order synthetic dark-store dataset generator
│   │   ├── train_models.py        # GradientBoostingRegressor & RandomForestClassifier trainer
│   │   └── artifacts/             # Committed eta_model.joblib, sla_risk_model.joblib, metrics.json
│   └── tests/                     # Pytest suite (state machine, ML bounds, checkout concurrency)
├── frontend/
│   └── src/
│       ├── api/client.js          # REST client (VITE_API_URL)
│       ├── composables/           # Auto-reconnecting WebSocket composable
│       ├── stores/                # Pinia stores (hubStore, cartStore)
│       ├── components/            # Storefront, CartDrawer, LiveOrderTracker, LiveDispatchMap, OpsConsole, LowStockPanel, RiderDispatchPanel, AnalyticsDashboard
│       └── tests/                 # Vitest unit tests
├── docker-compose.yml
└── render.yaml
```

- **Frontend:** Vue 3 (`<script setup>`), Vite, Pinia, Tailwind CSS, Leaflet.js, Chart.js, Lucide Vue Next, Vitest.
- **Backend:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy, WebSockets, SQLite (WAL mode default; PostgreSQL supported via `DATABASE_URL`), Pandas, Scikit-learn, Joblib, Pytest.

---

## Concurrency & Atomic Inventory Locking Strategy

To prevent overselling under concurrent checkout traffic for scarce dark-store inventory (such as the last remaining unit of a high-demand SKU):

1. **Deterministic Lock Ordering:** Cart line items are aggregated and sorted by `product_id` ascending prior to database updates to eliminate cross-transaction lock-order deadlocks.
2. **Conditional Atomic Decrement:** Every SKU executes an atomic SQL update:
   ```sql
   UPDATE store_inventory
   SET stock_available = stock_available - :qty,
       stock_reserved  = stock_reserved  + :qty
   WHERE store_id = :store_id
     AND product_id = :product_id
     AND stock_available >= :qty;
   ```
3. **Conflict Rollback:** If `rowcount != 1`, the transaction rolls back immediately and returns `HTTP 409 Conflict` with the exact SKU and remaining availability.
4. **Atomic Restoration:** Cancelling an order prior to dispatch (`PLACED`, `PICKING`, or `PACKED`) atomically restores `stock_available` and releases `stock_reserved` within the same transaction as the `order_events` audit insert.

---

## ML SLA & ETA Prediction Engine

The ML pipeline (`backend/ml/`) generates 2,500 synthetic historical dark-store orders incorporating Bangalore peak-hour congestion, picker aisle traversal, queue depth, and rider availability:

| Feature | Description |
| :--- | :--- |
| `item_count` | Total units in the order |
| `unique_aisles` | Distinct dark-store aisles required for picking |
| `active_queue_depth` | Current in-flight orders (`PLACED`, `PICKING`, `PACKED`) at the hub |
| `idle_riders` | Number of `IDLE` riders stationed at the hub |
| `distance_km` | Haversine distance from dark store to customer drop-off pin |
| `hour_of_day` | Order hour capturing morning and evening traffic congestion |

- **ETA Regression:** `GradientBoostingRegressor` (`eta_model.joblib`) predicting fulfillment duration in seconds (test MAE ~27s, R2 ~0.95).
- **SLA Breach Classifier:** `RandomForestClassifier` (`sla_risk_model.joblib`) predicting probability of exceeding the 600-second SLA window (test ROC-AUC ~0.976).
- Both `.joblib` artifacts are committed to the repository and loaded once during FastAPI lifespan startup for sub-millisecond inference on every checkout.

---

## Local Setup

### Option 1: Docker Compose (One Command)
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
# Backend Pytest suite (state machine, ML inference, checkout concurrency)
cd backend && .venv/bin/pytest -v

# Frontend Vitest suite (cart state & SLA utilities)
cd frontend && npm test
```

---

## Free-Tier Production Deployment (Render + Vercel)

1. **Backend on Render:**
   - Connect this repository on Render using `render.yaml` (or create a Web Service with Root Directory `backend`, Build Command `pip install -r requirements.txt`, and Start Command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`).
   - Set environment variable `FRONTEND_URL` to your deployed Vercel URL (e.g., `https://swifthub.vercel.app`).
   - `DATABASE_URL` defaults to SQLite (`sqlite:///./swifthub.db`) for zero-config startup and can be switched to PostgreSQL at any time.
2. **Frontend on Vercel:**
   - Import the repository on Vercel with Root Directory `frontend` (`frontend/vercel.json` configures Vite build and SPA rewrites).
   - Set environment variable `VITE_API_URL` to your Render backend URL (e.g., `https://swifthub-backend.onrender.com`). WebSocket URLs (`wss://`) are derived automatically.
