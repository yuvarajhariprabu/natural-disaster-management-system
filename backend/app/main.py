import asyncio
import datetime
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db, SessionLocal
from app.models import Node, SensorReading, Alert
from app.schemas import (
    NodeResponse, SensorReadingResponse, AlertResponse, 
    RiskStatusResponse, DashboardSummaryResponse
)
from app.risk_engine import calculate_risks, check_and_generate_alerts, calculate_node_status
from app.serial_gateway import start_serial_thread

# Create DB Tables (Auto-migration/init)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="D-SHIELD API Gateway", version="1.0.0")

# CORS Middleware for React Local Development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Seed Initial Nodes if Database is empty
def seed_nodes():
    db = SessionLocal()
    try:
        if not db.query(Node).first():
            print("D-SHIELD: Seeding initial nodes into database...")
            nodes = [
                Node(id="NODE1", node_name="Mountain Node", location="Landslide Risk Area", latitude=45.892, longitude=6.842, status="ONLINE", last_seen=datetime.datetime.utcnow()),
                Node(id="NODE2", node_name="River Node", location="Flood Risk Basin", latitude=45.885, longitude=6.850, status="ONLINE", last_seen=datetime.datetime.utcnow()),
                Node(id="NODE3", node_name="Field Aggregator", location="Base Operations Field", latitude=45.888, longitude=6.845, status="ONLINE", last_seen=datetime.datetime.utcnow())
            ]
            db.add_all(nodes)
            
            # Baseline Safe Readings
            now = datetime.datetime.utcnow()
            for i in range(10):
                t = now - datetime.timedelta(minutes=10 - i)
                db.add(SensorReading(node_id="NODE1", timestamp=t, soil_moisture=30.0 + i*0.2, vibration=0.12 + i*0.01))
                db.add(SensorReading(node_id="NODE2", timestamp=t, water_level=1.1 + i*0.02, temperature=19.5, pressure=1012.5))
                db.add(SensorReading(node_id="NODE3", timestamp=t, rainfall=0.0))
                
            db.commit()
    finally:
        db.close()

seed_nodes()

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                # Connection might be dead, handled during disconnection
                pass

manager = ConnectionManager()

def get_summary_data(db: Session) -> Dict[str, Any]:
    """Retrieve full dashboard summary data from DB state."""
    # Update node health statuses based on last_seen
    nodes = db.query(Node).all()
    for n in nodes:
        n.status = calculate_node_status(n.last_seen)
    db.commit()

    # Get risks
    landslide_risk, flood_risk, overall_risk, severity, reasons = calculate_risks(db)

    # Get latest readings per node
    latest_readings = []
    for nid in ["NODE1", "NODE2", "NODE3"]:
        reading = db.query(SensorReading).filter(SensorReading.node_id == nid).order_by(SensorReading.timestamp.desc()).first()
        if reading:
            latest_readings.append(reading)

    # Get active (unacknowledged) alerts
    active_alerts = db.query(Alert).filter(Alert.acknowledged == False).order_by(Alert.timestamp.desc()).all()

    # Format nodes
    node_responses = [NodeResponse.model_validate(n) for n in nodes]
    reading_responses = [SensorReadingResponse.model_validate(r) for r in latest_readings]
    alert_responses = [AlertResponse.model_validate(a) for a in active_alerts]

    return {
        "overall_risk": overall_risk,
        "landslide_risk": landslide_risk,
        "flood_risk": flood_risk,
        "severity": severity,
        "reasons": reasons,
        "nodes": [n.model_dump() for n in node_responses],
        "latest_readings": [r.model_dump() for r in reading_responses],
        "active_alerts": [a.model_dump() for a in alert_responses]
    }

# Callback to broadcast DB changes via WebSockets (Thread-safe)
loop = asyncio.get_event_loop()

def trigger_websocket_broadcast():
    db = SessionLocal()
    try:
        summary = get_summary_data(db)
        # Dispatch to the event loop running in the main thread
        asyncio.run_coroutine_threadsafe(manager.broadcast(summary), loop)
    except Exception as e:
        print(f"Error during WS broadcast: {e}")
    finally:
        db.close()

# Start background serial monitor
start_serial_thread(trigger_websocket_broadcast)

# --- REST ENDPOINTS ---

@app.get("/api/summary", response_model=DashboardSummaryResponse)
def get_summary(db: Session = Depends(get_db)):
    return get_summary_data(db)

@app.get("/api/nodes", response_model=List[NodeResponse])
def get_nodes(db: Session = Depends(get_db)):
    nodes = db.query(Node).all()
    for n in nodes:
        n.status = calculate_node_status(n.last_seen)
    db.commit()
    return nodes

@app.get("/api/readings", response_model=List[SensorReadingResponse])
def get_readings(node_id: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(SensorReading)
    if node_id:
        query = query.filter(SensorReading.node_id == node_id)
    return query.order_by(SensorReading.timestamp.desc()).limit(limit).all()

@app.get("/api/alerts", response_model=List[AlertResponse])
def get_alerts(db: Session = Depends(get_db)):
    return db.query(Alert).order_by(Alert.timestamp.desc()).all()

@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = True
    db.commit()
    trigger_websocket_broadcast()
    return {"status": "success", "alert_id": alert_id}

@app.post("/api/simulate")
def run_simulation(payload: Dict[str, str], db: Session = Depends(get_db)):
    scenario = payload.get("scenario", "normal")
    now = datetime.datetime.utcnow()
    
    # Ensure all nodes are online
    nodes = db.query(Node).all()
    for n in nodes:
        n.status = "ONLINE"
        n.last_seen = now
        n.packet_count += 1
        n.rssi = -70.0
        n.snr = 9.0

    if scenario == "reset":
        # Clear readings and alerts, recreate defaults
        db.query(SensorReading).delete()
        db.query(Alert).delete()
        
        # Reset counters
        for n in nodes:
            n.packet_count = 0
            n.last_seen = now
            
        # Re-add normal seed readings
        for i in range(10):
            t = now - datetime.timedelta(minutes=10 - i)
            db.add(SensorReading(node_id="NODE1", timestamp=t, soil_moisture=30.0 + i*0.2, vibration=0.1))
            db.add(SensorReading(node_id="NODE2", timestamp=t, water_level=1.1 + i*0.01, temperature=19.0, pressure=1013.0))
            db.add(SensorReading(node_id="NODE3", timestamp=t, rainfall=0.0))
        db.commit()
        trigger_websocket_broadcast()
        return {"status": "database reset to normal baseline"}

    # Base telemetry values
    soil_moisture = 35.0
    vibration = 0.15
    water_level = 1.3
    temperature = 20.2
    pressure = 1012.8
    rainfall = 0.0

    if scenario == "normal":
        pass # use default base values
        
    elif scenario == "rain":
        # Heavy rain starts
        rainfall = 38.5
        db.add(Alert(
            node_id="NODE3",
            alert_type="HEAVY_RAIN",
            severity="WARNING",
            message="HEAVY RAIN DETECTED: Local aggregator rain gauge reports 38.5 mm/h."
        ))

    elif scenario == "river":
        # River rising rapidly
        # We append a series of fast-rising readings to trigger rise-rate detection
        for i in range(4):
            t = now - datetime.timedelta(seconds=40 - i*10)
            db.add(SensorReading(
                node_id="NODE2", timestamp=t, 
                water_level=2.0 + i*0.9, # rising quickly!
                temperature=17.5, pressure=1010.2
            ))
        water_level = 4.8
        rainfall = 15.0 # moderate rain accompanying flood
        
    elif scenario == "landslide":
        # High landslide risk
        soil_moisture = 86.4
        vibration = 5.8
        rainfall = 25.0
        
    elif scenario == "critical":
        # Multi-disaster catastrophic scenario
        # 1. Rising river
        for i in range(4):
            t = now - datetime.timedelta(seconds=40 - i*10)
            db.add(SensorReading(
                node_id="NODE2", timestamp=t, 
                water_level=2.2 + i*0.8,
                temperature=16.8, pressure=1008.5
            ))
        water_level = 5.2
        # 2. Saturated mountains
        soil_moisture = 92.1
        vibration = 7.8
        # 3. Torrential rain
        rainfall = 55.4

    # Save final reading values
    db.add(SensorReading(node_id="NODE1", timestamp=now, soil_moisture=soil_moisture, vibration=vibration))
    db.add(SensorReading(node_id="NODE2", timestamp=now, water_level=water_level, temperature=temperature, pressure=pressure))
    db.add(SensorReading(node_id="NODE3", timestamp=now, rainfall=rainfall))

    db.commit()

    # Force risk engine update & alert evaluation
    landslide_risk, flood_risk, overall_risk, severity, reasons = calculate_risks(db)
    check_and_generate_alerts(db, landslide_risk, flood_risk, rainfall, reasons)

    trigger_websocket_broadcast()
    return {
        "status": f"simulated {scenario}",
        "landslide_risk": landslide_risk,
        "flood_risk": flood_risk,
        "overall_risk": overall_risk,
        "severity": severity
    }

# --- WEBSOCKET ENDPOINT ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send initial data immediately on connection
    db = SessionLocal()
    try:
        initial_data = get_summary_data(db)
        await websocket.send_json(initial_data)
    except Exception as e:
        print(f"Error sending initial ws data: {e}")
    finally:
        db.close()
        
    try:
        while True:
            # Keep connection alive, listen for client pings or acknowledgments
            data = await websocket.receive_text()
            # If client sends acknowledgment via ws, handle it
            try:
                msg = json.loads(data)
                if msg.get("type") == "ACK_ALERT":
                    alert_id = msg.get("alert_id")
                    db = SessionLocal()
                    alert = db.query(Alert).filter(Alert.id == alert_id).first()
                    if alert:
                        alert.acknowledged = True
                        db.commit()
                        trigger_websocket_broadcast()
                    db.close()
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
