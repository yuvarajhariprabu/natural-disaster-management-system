from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
import datetime
from app.database import Base

class Node(Base):
    __tablename__ = "nodes"
    
    id = Column(String, primary_key=True, index=True) # e.g. "NODE1", "NODE2", "NODE3"
    node_name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String, default="OFFLINE") # ONLINE, OFFLINE, STALE
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)
    rssi = Column(Float, nullable=True)
    snr = Column(Float, nullable=True)
    packet_count = Column(Integer, default=0)

    readings = relationship("SensorReading", back_populates="node")
    alerts = relationship("Alert", back_populates="node")

class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    node_id = Column(String, ForeignKey("nodes.id"), index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Node 1 parameters
    soil_moisture = Column(Float, nullable=True)
    vibration = Column(Float, nullable=True)
    
    # Node 2 parameters
    water_level = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    pressure = Column(Float, nullable=True)
    
    # Node 3 parameters
    rainfall = Column(Float, nullable=True)

    node = relationship("Node", back_populates="readings")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    node_id = Column(String, ForeignKey("nodes.id"), index=True, nullable=True)
    alert_type = Column(String, nullable=False) # e.g., "LANDSLIDE", "FLOOD", "HEAVY_RAIN", "COMMUNICATION"
    severity = Column(String, nullable=False) # SAFE, LOW, WARNING, HIGH, CRITICAL
    message = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    acknowledged = Column(Boolean, default=False)

    node = relationship("Node", back_populates="alerts")
