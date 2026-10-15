import threading
import time
import json
import serial
import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.config import settings
from app.models import Node, SensorReading
from app.risk_engine import calculate_risks, check_and_generate_alerts

# Global callback hook to broadcast WebSocket updates
broadcast_ws_message = None

def run_serial_listener():
    if not settings.USE_SERIAL:
        print("D-SHIELD: Serial gateway listener is disabled. Set USE_SERIAL=true to enable physical USB gateway reading.")
        return

    print(f"D-SHIELD: Starting serial listener on port {settings.SERIAL_PORT} @ {settings.SERIAL_BAUD} baud...")
    
    while True:
        ser = None
        try:
            ser = serial.Serial(settings.SERIAL_PORT, settings.SERIAL_BAUD, timeout=1)
            print(f"D-SHIELD: Serial port {settings.SERIAL_PORT} opened successfully.")
            while True:
                line = ser.readline()
                if not line:
                    continue
                try:
                    line_str = line.decode('utf-8').strip()
                    if not line_str:
                        continue
                    
                    print(f"D-SHIELD Serial Data Received: {line_str}")
                    
                    db = SessionLocal()
                    try:
                        parts = line_str.split(",")
                        node_id = parts[0].strip()
                        
                        if node_id == "NODE1" and len(parts) >= 4:
                            # format: NODE1,packet_id,soil_moisture,vibration,[rssi],[snr]
                            soil_m = float(parts[2])
                            vib = float(parts[3])
                            rssi = float(parts[4]) if len(parts) > 4 else -75.0
                            snr = float(parts[5]) if len(parts) > 5 else 8.0
                            
                            node = db.query(Node).filter(Node.id == node_id).first()
                            if node:
                                node.last_seen = datetime.datetime.utcnow()
                                node.status = "ONLINE"
                                node.packet_count += 1
                                node.rssi = rssi
                                node.snr = snr
                                
                            reading = SensorReading(
                                node_id=node_id, 
                                soil_moisture=soil_m, 
                                vibration=vib
                            )
                            db.add(reading)
                            
                        elif node_id == "NODE2" and len(parts) >= 5:
                            # format: NODE2,packet_id,water_level,temperature,pressure,[rssi],[snr]
                            wl = float(parts[2])
                            temp = float(parts[3])
                            press = float(parts[4])
                            rssi = float(parts[5]) if len(parts) > 5 else -80.0
                            snr = float(parts[6]) if len(parts) > 6 else 6.0
                            
                            node = db.query(Node).filter(Node.id == node_id).first()
                            if node:
                                node.last_seen = datetime.datetime.utcnow()
                                node.status = "ONLINE"
                                node.packet_count += 1
                                node.rssi = rssi
                                node.snr = snr
                                
                            reading = SensorReading(
                                node_id=node_id, 
                                water_level=wl, 
                                temperature=temp, 
                                pressure=press
                            )
                            db.add(reading)
                            
                        elif node_id == "NODE3" and len(parts) >= 3:
                            # format: NODE3,packet_id,rainfall,[rssi],[snr]
                            rain = float(parts[2])
                            rssi = float(parts[3]) if len(parts) > 3 else -65.0
                            snr = float(parts[4]) if len(parts) > 4 else 10.0
                            
                            node = db.query(Node).filter(Node.id == node_id).first()
                            if node:
                                node.last_seen = datetime.datetime.utcnow()
                                node.status = "ONLINE"
                                node.packet_count += 1
                                node.rssi = rssi
                                node.snr = snr
                                
                            reading = SensorReading(
                                node_id=node_id, 
                                rainfall=rain
                            )
                            db.add(reading)
                            
                        db.commit()
                        
                        # Recalculate risks using fresh database state
                        landslide_risk, flood_risk, overall_risk, severity, reasons = calculate_risks(db)
                        
                        # Generate any matching alerts based on new state
                        current_rain = db.query(SensorReading).filter(SensorReading.node_id == "NODE3").order_by(SensorReading.timestamp.desc()).first()
                        rain_val = current_rain.rainfall if current_rain else 0.0
                        check_and_generate_alerts(db, landslide_risk, flood_risk, rain_val, reasons)
                        
                        # Broadcast the data update to all websocket clients
                        if broadcast_ws_message:
                            broadcast_ws_message()
                            
                    except Exception as db_err:
                        db.rollback()
                        print(f"D-SHIELD: DB error during serial processing: {db_err}")
                    finally:
                        db.close()
                        
                except Exception as parse_err:
                    print(f"D-SHIELD: Error parsing incoming serial line: {parse_err}")
                    
        except Exception as conn_err:
            print(f"D-SHIELD: Serial port {settings.SERIAL_PORT} disconnected or failed to open: {conn_err}")
            if ser:
                try:
                    ser.close()
                except:
                    pass
            print("D-SHIELD: Re-trying to connect in 5 seconds...")
            time.sleep(5)

def start_serial_thread(ws_broadcast_callback):
    """Start serial reader in background daemon thread."""
    global broadcast_ws_message
    broadcast_ws_message = ws_broadcast_callback
    thread = threading.Thread(target=run_serial_listener, daemon=True)
    thread.start()
    return thread
