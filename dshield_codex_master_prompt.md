# Build Request: Offline Rural Disaster Monitoring System

Build a COMPLETE, RUNNABLE, production-quality hackathon prototype named **D-SHIELD (Disaster Sensing & Hazard Intelligence Early-Warning Layer)** for **“Real-Time Disaster Information Aggregation Using IoT Sensors.”** Do not give only explanations/mockups: generate the full project source code, configs, DB schema, firmware, frontend, backend, setup/run instructions, and sample/demo data so the UI works immediately even before physical hardware is connected.

## 1. Core Architecture
Use **3 ESP32 + 3 LoRa + antennas**:
- **Node 1 / Mountain:** ESP32 + LoRa + soil-moisture sensor + vibration/shock sensor → landslide-risk monitoring.
- **Node 2 / River:** ESP32 + LoRa + ultrasonic sensor + BMP280 → water-level, temperature, pressure/flood-risk monitoring.
- **Node 3 / Field Aggregator:** ESP32 + LoRa + rain sensor → rainfall monitoring + receives Node 1/2 LoRa packets + aggregates data + forwards to local gateway.
- Node 3 connects to a **local PC/gateway via USB/Serial**.
- Core operation MUST work **without internet**: Node1↔LoRa↔Node3 and Node2↔LoRa↔Node3; local gateway runs backend/DB/UI. Internet/cloud is optional only.
- Recommended data flow: **Sensors → ESP32/C++ → LoRa → Node3 → USB/Serial → FastAPI/Python → PostgreSQL → WebSocket → React/Vite UI**.
- Do NOT make Wi-Fi/cloud mandatory. Keep architecture modular for future expansion.

## 2. Required Tech Stack
**Firmware:** C/C++ with Arduino framework, Arduino IDE or PlatformIO; suitable LoRa and sensor libraries.
**Backend:** Python + FastAPI + SQLAlchemy + PostgreSQL.
**Frontend:** React + Vite + JavaScript/JSX + HTML/CSS.
**Realtime:** WebSocket preferred; REST polling fallback.
**Charts:** Recharts or equivalent.
**Map:** Leaflet/OpenStreetMap or equivalent; predefined demo coordinates are fine.
Keep dependencies minimal and Windows-friendly. Reuse this stack because the developer already knows Python, FastAPI, PostgreSQL, SQLAlchemy, React, Vite, JS, HTML/CSS.

## 3. Embedded Requirements
Create separate firmware/configuration for Node1, Node2, Node3. Include pin constants in one clearly editable section, sensor initialization, readings, calibration/filtering, validation, LoRa packet IDs/sequence numbers, timestamps where available, retry/error handling, node health/heartbeat, and configurable thresholds.
Node1 packet: `NODE1,packet_id,soil_moisture,vibration`.
Node2 packet: `NODE2,packet_id,water_level,temperature,pressure`.
Node3 measures rain and receives Node1/2; use a lightweight structured packet/JSON internally if appropriate but keep LoRa payload compact.
Node2 water level = `known_sensor_mounting_height - ultrasonic_distance`; make mounting height configurable.
Do not claim sensors guarantee disasters; describe outputs as **risk/early-warning conditions**.

## 4. Risk/Data-Fusion Engine
Implement explainable configurable scoring, not opaque AI:
- Landslide risk = soil moisture + vibration + optional rainfall influence.
- Flood risk = water level + **rate of water-level rise** + rainfall.
- Overall risk combines disaster risks and current environmental severity.
Use normalized scores and configurable thresholds producing **SAFE, LOW, WARNING, HIGH, CRITICAL**. Clearly label thresholds as demo/prototype values, not official emergency standards.
Detect trends from historical readings; e.g. rapidly rising water level increases flood risk.
Generate human-readable reasons, e.g. “Landslide risk elevated: high soil moisture + elevated vibration.”
Detect stale/missing packets and mark nodes/sensors **ONLINE/OFFLINE/STALE**.

## 5. Backend
Create a clean FastAPI application with:
- sensor ingestion endpoint(s)
- latest readings
- historical readings
- node status/health
- risk calculation
- alerts
- dashboard summary
- WebSocket realtime stream
- demo/simulation endpoints
Use SQLAlchemy models and PostgreSQL schema/tables:
`nodes(id,node_name,location,latitude,longitude,status,last_seen)`
`sensor_readings(id,node_id,timestamp,soil_moisture,vibration,water_level,temperature,pressure,rainfall)`
`alerts(id,node_id,alert_type,severity,message,timestamp,acknowledged)`
Add indexes where useful. Use Pydantic schemas, environment variables, CORS, validation, structured errors, logging, and clean service modules.
If PostgreSQL is unavailable during first launch, provide a clearly documented **demo mode** using SQLite/in-memory storage so the UI still runs; PostgreSQL remains the target deployment DB.

## 6. Frontend: FULL WORKING UI
Build a polished, responsive **single-page disaster command dashboard**, not a placeholder. It must run immediately with demo/simulated data and later switch to live backend data.
Required UI:
1. Header: D-SHIELD, “Offline Rural Disaster Monitoring”, connection indicator, current time/status, demo/live mode.
2. Large **Overall Risk** card with percentage, severity, explanation, and last update.
3. Three node cards:
   - Node 1 🏔️ Mountain: soil moisture, vibration, landslide risk, node health.
   - Node 2 🌊 River: water level, water-rise rate, temperature, pressure, flood risk, node health.
   - Node 3 🌧️ Aggregator: rainfall, LoRa reception, aggregation status, node health.
4. **Live alert panel** with severity, timestamp, source node, message, acknowledge action.
5. **Historical realtime charts**: soil moisture, vibration, water level/trend, rainfall, overall risk.
6. **Live map** with Node1/2/3 markers and severity status; clicking marker shows sensor values.
7. **Network/LoRa health**: packets received, last packet, RSSI/SNR if available, node online/offline, packet loss/error state.
8. **Data-source/status panel** showing Offline/Local/Internet optional mode.
9. Responsive layout for laptop/projector/mobile.
10. Accessible UI, loading/empty/error states, realistic demo data, no broken buttons.
Use CSS with a professional emergency-monitoring visual language; avoid excessive animations. Make critical alerts visually obvious but readable.

## 7. Demo/Simulation Mode
Because hardware may not be connected during development, include a **Demo Mode** that simulates changing sensor values and disasters. Provide controls such as:
- Normal/Safe
- Heavy Rain
- Rising River
- Landslide Risk
- Critical Combined Event
- Reset
Demo values must flow through the same backend/risk/UI pipeline as live data where practical.
Example scenario:
rain increases → soil moisture rises → vibration becomes elevated → landslide risk rises; simultaneously water level rises rapidly → flood risk rises → overall risk becomes CRITICAL → alert appears.
Do NOT hard-code UI-only fake cards disconnected from application state.

## 8. Offline-First Behavior
The UI must remain useful if internet is absent. Never depend on external map tiles, CDN fonts, remote APIs, or cloud services for core functionality. Use local assets/default map fallback where possible. Clearly show **LOCAL/OFFLINE** mode.
If the gateway is disconnected, show stale/offline state instead of pretending data is live.
ESP32 nodes should continue local sensor reading/risk evaluation and LoRa communication even without internet.

## 9. Project Structure
Create a clean monorepo similar to:
`/firmware/node1`
`/firmware/node2`
`/firmware/node3`
`/backend/app/{api,models,schemas,services,core,db}`
`/frontend/src/{components,pages,services,hooks,utils}`
plus `.env.example`, README, database migration/init scripts, requirements.txt/package.json, and any PlatformIO/Arduino configuration required.
Keep secrets/config out of source; provide `.env.example`.

## 10. API/UI Contract
Define consistent JSON models for:
`NodeStatus`, `SensorReading`, `RiskStatus`, `Alert`, `DashboardSummary`.
Example risk response:
`{ "landslide_risk": 82, "flood_risk": 76, "overall_risk": 85, "severity": "HIGH", "reasons": [...] }`.
WebSocket messages should update node readings, risk, alerts, and health without page refresh.
Frontend must handle backend unavailable gracefully and fall back to local/demo mode.

## 11. Reliability & Safety
Validate sensor ranges; reject malformed packets; ignore duplicates using packet IDs; track last-seen; handle LoRa timeout; handle sensor failure; prevent negative/invalid water levels; debounce/filter noisy vibration/rain readings where appropriate.
Never describe the prototype as guaranteeing landslide/flood prediction. It is a **multi-sensor disaster-risk monitoring and early-warning prototype**. Include a visible dashboard disclaimer that thresholds are demonstration values and require field calibration/official validation before real emergency use.

## 12. Deliverable Standard
Generate **all code needed to run the project**, not pseudocode. Ensure imports, paths, dependencies, environment variables, API routes, DB models, frontend API calls, WebSocket handling, demo mode, and styling are consistent.
Provide exact Windows commands for:
1. backend virtual environment/install/start;
2. PostgreSQL setup and DB initialization;
3. frontend npm install/start;
4. firmware build/upload;
5. serial gateway operation;
6. full demo mode without hardware.
Include a concise troubleshooting section.
Before finishing, verify the project for obvious syntax/import/configuration errors and ensure the frontend has a complete working UI rather than placeholders.

## 13. Hackathon Demo Flow
The final demo should visibly show:
**Safe → Heavy Rain → Soil Moisture Rising → Vibration Elevated → Landslide HIGH → River Rising → Flood HIGH → Combined CRITICAL → Alert + map/status/chart updates.**
The key pitch is: **distributed LoRa sensor network + local data fusion + offline-first operation + real-time risk dashboard for rural disaster monitoring.**
