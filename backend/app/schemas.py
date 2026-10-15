from pydantic import BaseModel
from typing import List, Optional
import datetime

class NodeBase(BaseModel):
    id: str
    node_name: str
    location: str
    latitude: float
    longitude: float

class NodeResponse(NodeBase):
    status: str
    last_seen: datetime.datetime
    rssi: Optional[float] = None
    snr: Optional[float] = None
    packet_count: int

    class Config:
        from_attributes = True

class SensorReadingBase(BaseModel):
    node_id: str
    soil_moisture: Optional[float] = None
    vibration: Optional[float] = None
    water_level: Optional[float] = None
    temperature: Optional[float] = None
    pressure: Optional[float] = None
    rainfall: Optional[float] = None

class SensorReadingCreate(SensorReadingBase):
    pass

class SensorReadingResponse(SensorReadingBase):
    id: int
    timestamp: datetime.datetime

    class Config:
        from_attributes = True

class AlertBase(BaseModel):
    node_id: Optional[str] = None
    alert_type: str
    severity: str
    message: str

class AlertResponse(AlertBase):
    id: int
    timestamp: datetime.datetime
    acknowledged: bool

    class Config:
        from_attributes = True

class RiskStatusResponse(BaseModel):
    landslide_risk: float
    flood_risk: float
    overall_risk: float
    severity: str
    reasons: List[str]

class DashboardSummaryResponse(BaseModel):
    overall_risk: float
    severity: str
    reasons: List[str]
    nodes: List[NodeResponse]
    latest_readings: List[SensorReadingResponse]
    active_alerts: List[AlertResponse]
