# D-SHIELD: Disaster Sensing & Hazard Intelligence Early-Warning Layer

D-SHIELD is a complete, runnable, production-quality hackathon prototype for an **Offline-First, Rural Disaster Monitoring & Early-Warning System**. It utilizes distributed IoT sensor nodes communicating via LoRa to aggregate regional environmental data, perform explainable local data-fusion risk calculations, and display threat assessments on a premium dark-themed command center dashboard.

---

## 1. System Architecture Overview

```mermaid
graph TD
    subgraph Remote Field (Wireless LoRa Network)
        Node1["🏔️ Node 1 (Mountain)<br>ESP32 + Soil Moisture + Vibration"] -- LoRa Packet<br>868/915 MHz --> Node3
        Node2["🌊 Node 2 (River)<br>ESP32 + Ultrasonic + BMP280"] -- LoRa Packet<br>868/915 MHz --> Node3
    end

    subgraph Aggregator Base (Wired Gateway)
        Node3["🌧️ Node 3 (Aggregator)<br>ESP32 + Rain Sensor + LoRa Receiver"] -- USB CDC<br>Serial Bridge --> GatewayPC["💻 Local PC / Gateway"]
    end

    subgraph Software Stack (Gateway PC)
        GatewayPC --> SerialGateway["Serial Gateway Worker<br>(Python background thread)"]
        GatewayPC --> FastAPI["FastAPI Backend<br>(Python API + Uvicorn)"]
        SerialGateway --> DB[("Database Engine<br>(PostgreSQL / SQLite Auto-Fallback)")]
        FastAPI <--> DB
        FastAPI -- Real-time WebSockets / REST --> ReactApp["React / Vite Dashboard<br>(Command UI + Leaflet Map)"]
        ReactApp -- Control Simulation Scenarios --> FastAPI
    end
```

---

## 2. Hardware Engineering Part

The physical hardware architecture uses **three ESP32 development boards** and **three SX1276/SX1278 RFM95 LoRa transceiver modules**.

### A. Pin Connection Maps

All three nodes share the same **SPI Pin Mappings** between the ESP32 and the LoRa transceiver module:

| LoRa module pin | ESP32 Pin | Description |
| :--- | :--- | :--- |
| **MOSI** | **GPIO 27** | Master Out Slave In |
| **MISO** | **GPIO 19** | Master In Slave Out |
| **SCK** | **GPIO 5** | Serial Clock |
| **NSS / CS** | **GPIO 18** | Chip Select |
| **RST** | **GPIO 14** | Reset Pin |
| **DIO0** | **GPIO 26** | Interrupt Request (Tx/Rx done) |
| **VCC** | **3.3V** | Power (Use decoupling capacitors if noisy) |
| **GND** | **GND** | Ground |

---

### B. Node-Specific Wiring & Sensor Specifications

#### Node 1: Mountain Landslide Node
Monitors environmental indicators of land slip or landslide events.
- **Soil Moisture Sensor (e.g., Capacitive v1.2):**
  - VCC -> 3.3V
  - GND -> GND
  - AOUT -> **GPIO 34 (ADC1_CH6)**
- **Vibration Sensor (e.g., SW-420 or Piezo Sensor):**
  - VCC -> 3.3V / 5V
  - GND -> GND
  - AOUT/DOUT -> **GPIO 35 (ADC1_CH7)**

#### Node 2: River Flood Node
Monitors water level heights, atmospheric pressure, and weather parameters.
- **HC-SR04 Ultrasonic Distance Sensor:**
  - VCC -> 5V (Use level shifter or resistor divider on Echo if using 3.3V logic)
  - GND -> GND
  - Trig -> **GPIO 32** (Output)
  - Echo -> **GPIO 33** (Input)
- **BMP280 Temperature & Pressure Sensor:**
  - VCC -> 3.3V
  - GND -> GND
  - SDA -> **GPIO 21** (I2C SDA)
  - SCL -> **GPIO 22** (I2C SCL)

#### Node 3: Aggregator / Rain Gauge Node
Collects local precipitation data and listens for packets from Nodes 1 & 2.
- **Raindrop / Tipping Bucket Sensor:**
  - VCC -> 3.3V
  - GND -> GND
  - AOUT -> **GPIO 36 (SVP)**
- **Wired Connection:**
  - Connects to the Gateway PC via **USB-to-UART Serial** (using CP2102 or CH340 on the ESP32 board).

---

### C. LoRa Payload & Radio Protocols

To keep LoRa packet payloads compact, lightweight, and fast to transmit (maximizing battery life and minimizing airtime collisions), data is packed into comma-separated CSV structures:

1. **Node 1 Packet:**
   `NODE1,<packet_id>,<soil_moisture_percent>,<vibration_g>`
   *Example:* `NODE1,142,55.4,1.15`

2. **Node 2 Packet:**
   `NODE2,<packet_id>,<water_level_m>,<temperature_c>,<pressure_hpa>`
   *Example:* `NODE2,142,2.45,21.5,1012.35`

3. **Serial Forwarding Protocol (Node 3 -> PC):**
   When Node 3 receives a packet, it appends the received radio signal strength indicators (**RSSI** and **SNR**) and prints the line to the Serial console. It also reads its local rain sensor periodically:
   - *Forwarded Node 1:* `NODE1,142,55.4,1.15,-72.0,9.5`
   - *Forwarded Node 2:* `NODE2,142,2.45,21.5,1012.35,-85.0,7.0`
   - *Aggregator Rain:* `NODE3,105,12.5,-45.0,12.0`

---

## 3. Software Engineering Part

The software is structured as a Python FastAPI server running a SQLite/PostgreSQL database and communicating with a single-page React client application.

```text
/backend
  /app
    config.py         -> Loads settings from .env using Pydantic BaseSettings
    database.py       -> Initiates DB Connection; falls back to SQLite automatically if PostgreSQL is down
    models.py         -> ORM tables (Nodes, SensorReadings, Alerts)
    schemas.py        -> Pydantic types for request/response serialization
    risk_engine.py    -> Contains data-fusion early-warning mathematics
    serial_gateway.py -> Spawns background thread to parse COM port serial buffers
    main.py           -> Handles endpoints, seeds db, handles WebSocket brokers
  run.py              -> Boots backend via Uvicorn
  test_simulation.py  -> Python test client validating endpoints & calculations
/frontend
  /src
    App.jsx           -> Layout, WebSocket connections, Leaflet Map, Recharts timeline charts
    index.css         -> Neon dark cyber-emergency design CSS variables & overrides
  package.json        -> React build configurations
```

---

### A. Explainable Data-Fusion Risk Engine

The D-SHIELD risk engine avoids opaque black-box AI algorithms. It calculates threats deterministically using explainable, configurable logic:

#### 1. Landslide Risk ($R_{\text{land}}$)
Combines soil saturation, ground shock vibration peaks, and rainfall trends:
$$R_{\text{land}} = (S_{\text{soil}} \times 0.5) + (S_{\text{vib}} \times 0.3) + S_{\text{rain\_bonus}}$$
- **Soil Factor ($S_{\text{soil}}$):** Normalizes soil moisture percent against configured thresholds:
  - If $< \text{WARN}$: Maps linearly to $0\% - 30\%$
  - If $\text{WARN} \le \text{moisture} < \text{CRIT}$: Maps to $30\% - 70\%$
  - If $\ge \text{CRIT}$: Maps to $70\% - 100\%$
- **Vibration Factor ($S_{\text{vib}}$):** Normalizes maximum ground vibration in $g$-force.
- **Rainfall Bonus ($S_{\text{rain\_bonus}}$):** If precipitation rate is high ($>10$ mm/h), adds up to $20\%$ to the threat score.

#### 2. Flood Risk ($R_{\text{flood}}$)
Combines the absolute river height, rate of water level rise (derivative), and rainfall metrics:
$$R_{\text{flood}} = (S_{\text{level}} \times 0.5) + (S_{\text{rise}} \times 0.3) + S_{\text{rain\_bonus}}$$
- **Rate of Rise ($S_{\text{rise}}$):** The system calculates a moving average derivative of the water level over the last 5 readings:
  $$\text{Rise Rate} = \frac{\Delta \text{Water Level}}{\Delta \text{Time}}$$
  Rapid changes ($>1.0$ meters/minute) trigger maximum risk parameters.

#### 3. Overall Alert Severity Categorization
$$\text{Overall Risk} = \max(R_{\text{land}}, R_{\text{flood}})$$
- **SAFE:** $< 25\%$
- **LOW:** $25\% - 50\%$
- **WARNING:** $50\% - 70\%$
- **HIGH:** $70\% - 85\%$
- **CRITICAL:** $\ge 85\%$

---

### B. Gateway Serial Listener (`app/serial_gateway.py`)
Spawns a daemon thread in Python that listens to the designated gateway serial port. When a packet is read, the listener:
1. Parses the CSV payload based on the header token (`NODE1`, `NODE2`, or `NODE3`).
2. Persists the sensor reading into the SQL database (`sensor_readings` table).
3. Updates node health fields (`nodes` table) with the current timestamp, RSSI, and SNR.
4. Executes the **Risk Engine** to evaluate threat levels.
5. Invokes the WebSocket manager to broadcast updates to all active UI clients.

---

### C. WebSocket Broker with Polling Fallback (`frontend/src/App.jsx`)
The dashboard connects to `ws://localhost:8000/ws`. 
- **WebSocket updates:** Instantly push new packet events to the React UI without refreshing the page.
- **Automatic REST Fallback:** If the local gateway loses connection or is restarted, the React app detects the socket termination and falls back to fetching dashboard state using REST HTTP polling (`GET /api/summary`) every 3 seconds while trying to re-establish the WebSocket connection in the background.

---

### D. REST API Endpoints Map

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/api/summary` | Returns overall risk status, reasoning logs, node health states, latest readings, and active alerts. |
| **GET** | `/api/nodes` | List status, coordinates, link stats (RSSI/SNR), and last seen timestamps of all nodes. |
| **GET** | `/api/readings` | Returns historical telemetry data points (for chart rendering). |
| **GET** | `/api/alerts` | Returns a list of all early warning alerts. |
| **POST** | `/api/alerts/{id}/acknowledge` | Marks a warning alert as acknowledged (hides it from the main board). |
| **POST** | `/api/simulate` | Forces database parameters to simulate event scenarios. |

---

## 4. Setting Up & Running the Application

### Prerequisites
1. **Python 3.10+** (Ensure it is added to your environment `PATH`).
2. **Node.js 18+** (Includes npm package manager).

---

### Step 1: Clone and Configure Environment
Copy `.env.example` to `.env` in the root folder:
```powershell
cp .env.example .env
```
Ensure `USE_SERIAL=false` if you want to run the application in **Simulation Mode** (without physical ESP32 hardware connected).

---

### Step 2: Initialize Backend Server
Activate a virtual environment, install requirements, and run the backend:
```powershell
# 1. Open PowerShell and create venv
python -m venv venv

# 2. Bypass PowerShell execution policies if script execution is blocked:
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# 3. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 4. Install backend requirements
pip install -r backend/requirements.txt

# 5. Start the backend app
python backend/run.py
```
The console logs will confirm database tables were successfully created, and that the app is listening on `http://localhost:8000`.

---

### Step 3: Initialize Frontend Client
Open a second PowerShell window:
```powershell
# 1. Enter the frontend directory
cd frontend

# 2. Run the Vite development server
npm run dev
```
The command dashboard UI is now running on [http://localhost:5173](http://localhost:5173).

---

### Step 4: Run Automated Verification Tests
Validate backend APIs and early warning calculations by running the validation script:
```powershell
# In a venv-activated terminal
python backend/test_simulation.py
```

---

## 5. Hackathon Demonstration Walkthrough

Use the **Simulation Controller Panel** (top-right card of the dashboard) to demonstrate the real-time processing flow:

1. **Step 1: Normal Safe State**
   - Click **Safe Baseline**.
   - **Result:** The overall threat indicator is green and reads **0% SAFE**. The map markers are green. Reasons indicate metrics are within safe limits.
2. **Step 2: Rainfall Begins**
   - Click **Heavy Rain**.
   - **Result:** Aggregator Node registers rainfall. Visual alerts banner triggers: `"HEAVY RAIN DETECTED"`. Landslide and flood risk indices increase.
3. **Step 3: River Level Rises**
   - Click **Rising River**.
   - **Result:** River Node level jumps to $4.8$ meters. Historical charts show a sharp upward slope. Flood Risk rises, transitioning the dashboard status to **WARNING** (Orange markers).
4. **Step 4: Ground Activity**
   - Click **Landslide Risk**.
   - **Result:** Soil moisture is saturated ($86.4\%$) and seismic shock registers $5.8g$ vibration. Landslide Risk goes to critical levels.
5. **Step 5: Combined Critical Catastrophe**
   - Click **Critical Event**.
   - **Result:** Combined heavy rain, rapid river rise, and landslide metrics. Overall threat index flashes **CRITICAL** (Red dial at $95\%$). Map markers turn red, and specific text alert logs show actionable diagnostic warnings (e.g., soil saturation, rapid river rise).
6. **Step 6: Reset**
   - Click **Reset Database** to restore baseline metrics and acknowledge any active warnings.
