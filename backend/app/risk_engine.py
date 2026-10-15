import datetime
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models import Node, SensorReading, Alert
from app.config import settings

def calculate_node_status(last_seen: datetime.datetime) -> str:
    """Determine node health status based on last seen timestamp."""
    if not last_seen:
        return "OFFLINE"
    now = datetime.datetime.utcnow()
    diff = (now - last_seen).total_seconds()
    if diff > 90:
        return "OFFLINE"
    elif diff > 30:
        return "STALE"
    return "ONLINE"

def get_water_level_rise_rate(db: Session) -> float:
    """
    Calculate the rate of water level rise (meters per minute)
    using the last few sensor readings of Node 2.
    """
    readings = (
        db.query(SensorReading)
        .filter(SensorReading.node_id == "NODE2")
        .filter(SensorReading.water_level.isnot(None))
        .order_by(SensorReading.timestamp.desc())
        .limit(5)
        .all()
    )
    
    if len(readings) < 2:
        return 0.0
    
    # Simple derivative estimation
    # Let's compute average change between adjacent points
    rates = []
    for i in range(len(readings) - 1):
        curr = readings[i]
        prev = readings[i+1]
        time_diff = (curr.timestamp - prev.timestamp).total_seconds() / 60.0
        val_diff = curr.water_level - prev.water_level
        if time_diff > 0:
            rates.append(val_diff / time_diff)
            
    if not rates:
        return 0.0
        
    # Return average rate of rise, ignore negative changes (receding water doesn't add to flood risk)
    positive_rates = [r for r in rates if r > 0]
    if not positive_rates:
        return 0.0
    return sum(positive_rates) / len(positive_rates)

def calculate_risks(db: Session) -> Tuple[float, float, float, str, List[str]]:
    """
    Data Fusion & Early-Warning Calculations.
    Combines readings from Mountain Node (NODE1), River Node (NODE2), and Field Aggregator (NODE3).
    Returns (landslide_risk, flood_risk, overall_risk, severity, reasons)
    """
    # Fetch latest readings for each node
    latest_n1 = (
        db.query(SensorReading)
        .filter(SensorReading.node_id == "NODE1")
        .order_by(SensorReading.timestamp.desc())
        .first()
    )
    latest_n2 = (
        db.query(SensorReading)
        .filter(SensorReading.node_id == "NODE2")
        .order_by(SensorReading.timestamp.desc())
        .first()
    )
    latest_n3 = (
        db.query(SensorReading)
        .filter(SensorReading.node_id == "NODE3")
        .order_by(SensorReading.timestamp.desc())
        .first()
    )

    reasons = []
    
    # 1. Landslide Risk Calculations
    soil_moisture = latest_n1.soil_moisture if (latest_n1 and latest_n1.soil_moisture is not None) else 0.0
    vibration = latest_n1.vibration if (latest_n1 and latest_n1.vibration is not None) else 0.0
    rainfall = latest_n3.rainfall if (latest_n3 and latest_n3.rainfall is not None) else 0.0
    
    # Normalize Soil Moisture factor (0 to 100)
    if soil_moisture < settings.LANDSLIDE_SOIL_MOISTURE_WARN:
        sm_factor = (soil_moisture / settings.LANDSLIDE_SOIL_MOISTURE_WARN) * 30.0
    elif soil_moisture < settings.LANDSLIDE_SOIL_MOISTURE_CRIT:
        sm_factor = 30.0 + ((soil_moisture - settings.LANDSLIDE_SOIL_MOISTURE_WARN) / 
                            (settings.LANDSLIDE_SOIL_MOISTURE_CRIT - settings.LANDSLIDE_SOIL_MOISTURE_WARN)) * 40.0
    else:
        sm_factor = 70.0 + (min(soil_moisture - settings.LANDSLIDE_SOIL_MOISTURE_CRIT, 20.0) / 20.0) * 30.0
        
    # Normalize Vibration factor (0 to 100)
    if vibration < settings.LANDSLIDE_VIBRATION_WARN:
        vib_factor = (vibration / settings.LANDSLIDE_VIBRATION_WARN) * 30.0
    elif vibration < settings.LANDSLIDE_VIBRATION_CRIT:
        vib_factor = 30.0 + ((vibration - settings.LANDSLIDE_VIBRATION_WARN) / 
                             (settings.LANDSLIDE_VIBRATION_CRIT - settings.LANDSLIDE_VIBRATION_WARN)) * 40.0
    else:
        vib_factor = 70.0 + (min(vibration - settings.LANDSLIDE_VIBRATION_CRIT, 5.0) / 5.0) * 30.0

    # Optional rainfall influence on Landslide Risk
    rain_influence = 0.0
    if rainfall > 10.0:
        rain_influence = min((rainfall - 10.0) / 40.0 * 20.0, 20.0) # Up to 20% extra risk for heavy rain
        
    landslide_risk = (sm_factor * 0.5) + (vib_factor * 0.3) + rain_influence
    landslide_risk = min(max(landslide_risk, 0.0), 100.0)
    
    # Landslide reasons
    if soil_moisture >= settings.LANDSLIDE_SOIL_MOISTURE_CRIT:
        reasons.append(f"Landslide warning: Critical soil saturation detected ({soil_moisture:.1f}%).")
    elif soil_moisture >= settings.LANDSLIDE_SOIL_MOISTURE_WARN:
        reasons.append(f"Landslide warning: Elevated soil moisture ({soil_moisture:.1f}%).")
        
    if vibration >= settings.LANDSLIDE_VIBRATION_CRIT:
        reasons.append(f"Landslide warning: Critical ground vibrations detected ({vibration:.2f}g).")
    elif vibration >= settings.LANDSLIDE_VIBRATION_WARN:
        reasons.append(f"Landslide warning: Elevated seismic/vibration activity detected ({vibration:.2f}g).")

    # 2. Flood Risk Calculations
    water_level = latest_n2.water_level if (latest_n2 and latest_n2.water_level is not None) else 0.0
    rise_rate = get_water_level_rise_rate(db)
    
    # Normalize Water Level factor
    if water_level < settings.FLOOD_WATER_LEVEL_WARN:
        wl_factor = (water_level / settings.FLOOD_WATER_LEVEL_WARN) * 40.0
    elif water_level < settings.FLOOD_WATER_LEVEL_CRIT:
        wl_factor = 40.0 + ((water_level - settings.FLOOD_WATER_LEVEL_WARN) / 
                            (settings.FLOOD_WATER_LEVEL_CRIT - settings.FLOOD_WATER_LEVEL_WARN)) * 45.0
    else:
        wl_factor = 85.0 + (min(water_level - settings.FLOOD_WATER_LEVEL_CRIT, 2.0) / 2.0) * 15.0

    # Normalize Water Rise Rate factor
    if rise_rate < settings.FLOOD_RISE_RATE_WARN:
        rate_factor = (rise_rate / settings.FLOOD_RISE_RATE_WARN) * 40.0
    elif rise_rate < settings.FLOOD_RISE_RATE_CRIT:
        rate_factor = 40.0 + ((rise_rate - settings.FLOOD_RISE_RATE_WARN) / 
                              (settings.FLOOD_RISE_RATE_CRIT - settings.FLOOD_RISE_RATE_WARN)) * 45.0
    else:
        rate_factor = 85.0 + (min(rise_rate - settings.FLOOD_RISE_RATE_CRIT, 2.0) / 2.0) * 15.0
        
    # Rain factor on Flood
    rain_flood_factor = 0.0
    if rainfall > 5.0:
        rain_flood_factor = min(rainfall / 50.0 * 20.0, 20.0) # Up to 20% extra risk
        
    flood_risk = (wl_factor * 0.5) + (rate_factor * 0.3) + rain_flood_factor
    flood_risk = min(max(flood_risk, 0.0), 100.0)
    
    # Flood reasons
    if water_level >= settings.FLOOD_WATER_LEVEL_CRIT:
        reasons.append(f"Flood warning: Critical river water levels ({water_level:.2f}m).")
    elif water_level >= settings.FLOOD_WATER_LEVEL_WARN:
        reasons.append(f"Flood warning: River water levels elevated ({water_level:.2f}m).")
        
    if rise_rate >= settings.FLOOD_RISE_RATE_CRIT:
        reasons.append(f"Flood warning: River water level rising at a CRITICAL rate ({rise_rate:.2f} m/min).")
    elif rise_rate >= settings.FLOOD_RISE_RATE_WARN:
        reasons.append(f"Flood warning: River water level rising rapidly ({rise_rate:.2f} m/min).")

    # 3. Aggregator Node alerts
    if rainfall > 40.0:
        reasons.append(f"Field Alert: Torrential downpour detected ({rainfall:.1f}mm).")
    elif rainfall > 20.0:
        reasons.append(f"Field Alert: Heavy rainfall detected ({rainfall:.1f}mm).")

    # 4. Overall Severity Fusion
    overall_risk = max(landslide_risk, flood_risk)
    
    # Map Overall Risk to Severity Statuses
    if overall_risk < 25:
        severity = "SAFE"
    elif overall_risk < 50:
        severity = "LOW"
    elif overall_risk < 70:
        severity = "WARNING"
    elif overall_risk < 85:
        severity = "HIGH"
    else:
        severity = "CRITICAL"

    if len(reasons) == 0:
        reasons.append("Environmental metrics are within safe operational limits.")

    return landslide_risk, flood_risk, overall_risk, severity, reasons

def check_and_generate_alerts(db: Session, landslide_risk: float, flood_risk: float, rainfall: float, active_reasons: List[str]):
    """
    Check current risk scores and automatically create records in the alerts database table
    if they cross thresholds. Deduplicates similar active alerts.
    """
    # Helper to check if similar alert was created in the last 2 minutes
    def has_recent_alert(node_id: str, alert_type: str, severity: str) -> bool:
        two_mins_ago = datetime.datetime.utcnow() - datetime.timedelta(minutes=2)
        exists = (
            db.query(Alert)
            .filter(Alert.node_id == node_id)
            .filter(Alert.alert_type == alert_type)
            .filter(Alert.severity == severity)
            .filter(Alert.timestamp >= two_mins_ago)
            .first()
        )
        return exists is not None

    # Node 1 - Landslide risk alert
    if landslide_risk >= 85 and not has_recent_alert("NODE1", "LANDSLIDE", "CRITICAL"):
        db.add(Alert(
            node_id="NODE1",
            alert_type="LANDSLIDE",
            severity="CRITICAL",
            message="CRITICAL LANDSLIDE HAZARD: Soil moisture is saturated and high vibrations detected."
        ))
    elif landslide_risk >= 70 and not has_recent_alert("NODE1", "LANDSLIDE", "HIGH"):
        db.add(Alert(
            node_id="NODE1",
            alert_type="LANDSLIDE",
            severity="HIGH",
            message="HIGH LANDSLIDE RISK: Elevated vibration readings and high soil moisture."
        ))
    elif landslide_risk >= 50 and not has_recent_alert("NODE1", "LANDSLIDE", "WARNING"):
        db.add(Alert(
            node_id="NODE1",
            alert_type="LANDSLIDE",
            severity="WARNING",
            message="LANDSLIDE WARNING: Soil moisture levels are rising."
        ))

    # Node 2 - Flood risk alert
    if flood_risk >= 85 and not has_recent_alert("NODE2", "FLOOD", "CRITICAL"):
        db.add(Alert(
            node_id="NODE2",
            alert_type="FLOOD",
            severity="CRITICAL",
            message="CRITICAL FLOOD HAZARD: River water levels are critical and rising rapidly."
        ))
    elif flood_risk >= 70 and not has_recent_alert("NODE2", "FLOOD", "HIGH"):
        db.add(Alert(
            node_id="NODE2",
            alert_type="FLOOD",
            severity="HIGH",
            message="HIGH FLOOD RISK: Water level exceeds safety threshold."
        ))
    elif flood_risk >= 50 and not has_recent_alert("NODE2", "FLOOD", "WARNING"):
        db.add(Alert(
            node_id="NODE2",
            alert_type="FLOOD",
            severity="WARNING",
            message="FLOOD WARNING: River water level rising."
        ))

    # Node 3 - Heavy rain alert
    if rainfall >= 40.0 and not has_recent_alert("NODE3", "HEAVY_RAIN", "HIGH"):
        db.add(Alert(
            node_id="NODE3",
            alert_type="HEAVY_RAIN",
            severity="HIGH",
            message=f"TORRENTIAL RAIN: Local rainfall is at {rainfall:.1f} mm/h."
        ))
    elif rainfall >= 20.0 and not has_recent_alert("NODE3", "HEAVY_RAIN", "WARNING"):
        db.add(Alert(
            node_id="NODE3",
            alert_type="HEAVY_RAIN",
            severity="WARNING",
            message=f"HEAVY RAIN DETECTED: Precipitation is {rainfall:.1f} mm/h."
        ))

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error persisting generated alerts: {e}")
