from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

Base = declarative_base()

# Attempt to connect to PostgreSQL. If it fails, fallback to SQLite.
try:
    engine = create_engine(settings.DATABASE_URL)
    # Perform a quick connection test
    with engine.connect() as conn:
        pass
    print("D-SHIELD: Connected to PostgreSQL database successfully.")
except Exception as e:
    print(f"D-SHIELD: PostgreSQL connection failed: {e}")
    print("D-SHIELD: Falling back to local SQLite database (dshield.db).")
    engine = create_engine(
        "sqlite:///dshield.db",
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
