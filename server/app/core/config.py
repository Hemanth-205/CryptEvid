import os
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "CRYPTEVID Forensic Platform"
    API_V1_STR: str = "/api"
    
    # MongoDB Config (supports MONGODB_URL, MONGO_URL from Railway, or MONGO_URI)
    MONGODB_URL: str = os.getenv("MONGODB_URL") or os.getenv("MONGO_URL") or os.getenv("MONGO_URI") or "mongodb://localhost:27017"
    DATABASE_NAME: str = os.getenv("DATABASE_NAME") or "macro"
    
    # JWT Config
    JWT_SECRET_KEY: str = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY") or "supersecretkey_change_in_production_for_forensic_platform"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 Hours
    
    # Gemini AI Config
    GEMINI_API_KEY: str = ""
    
    # Storage Config
    UPLOAD_DIR: str = "./uploads"
    EVIDENCE_STORAGE_DIR: str = "./evidence_storage"
    # Backup storage is physically isolated from working evidence copies
    BACKUP_STORAGE_DIR: str = "./evidence_storage/backups"
    
    # Simulation Mode for ESP32
    SIMULATION_MODE: bool = True
    
    # Server Details
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Hardware USB Serial Bridge Config
    HARDWARE_BRIDGE_SECRET: str = os.getenv("HARDWARE_BRIDGE_SECRET") or "cryptevid_usb_bridge_secret_dev"
    ESP32_COM_PORT: str = os.getenv("ESP32_COM_PORT") or "COM5"
    ESP32_BAUD_RATE: int = int(os.getenv("ESP32_BAUD_RATE") or "115200")

    model_config = ConfigDict(case_sensitive=True, env_file=".env", extra="ignore")

settings = Settings()

# Ensure Upload, Evidence Storage, and Backup directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.EVIDENCE_STORAGE_DIR, exist_ok=True)
os.makedirs(settings.BACKUP_STORAGE_DIR, exist_ok=True)
