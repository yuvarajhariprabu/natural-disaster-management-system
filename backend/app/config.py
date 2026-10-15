import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/dshield"
    SERIAL_PORT: str = "COM3"
    SERIAL_BAUD: int = 115200
    USE_SERIAL: bool = False
    
    LANDSLIDE_SOIL_MOISTURE_WARN: float = 60.0
    LANDSLIDE_SOIL_MOISTURE_CRIT: float = 80.0
    LANDSLIDE_VIBRATION_WARN: float = 2.5
    LANDSLIDE_VIBRATION_CRIT: float = 5.0
    
    FLOOD_WATER_LEVEL_WARN: float = 3.0
    FLOOD_WATER_LEVEL_CRIT: float = 4.5
    FLOOD_RISE_RATE_WARN: float = 0.5
    FLOOD_RISE_RATE_CRIT: float = 1.0
    
    ULTRASONIC_MOUNTING_HEIGHT: float = 5.0

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
