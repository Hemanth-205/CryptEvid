from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal
from datetime import datetime

class HardwareSerialEventPayload(BaseModel):
    event_id: Optional[str] = Field(None, description="Client or Bridge generated unique UUID")
    protocol_version: int = Field(1, description="Protocol version, default 1")
    status: Literal["GRANTED", "DENIED"] = Field(..., description="Authentication outcome reported by ESP32")
    uid: str = Field(..., min_length=1, max_length=64, description="RFID UID string from sensor")
    reason: str = Field(..., min_length=1, max_length=128, description="Reason code such as AUTH_SUCCESS, AUTH_FAILED")
    device_id: str = Field("ESP32_USB", description="Hardware ingestion device identifier")
    raw_message: Optional[str] = Field(None, max_length=256, description="Original unparsed serial line")
    timestamp: Optional[str] = Field(None, description="ISO timestamp from sender")

class HardwareBridgeHeartbeatPayload(BaseModel):
    port: str = Field("COM5", max_length=32, description="Active Windows COM port")
    status: Literal["Connected", "Disconnected", "Error"] = Field("Connected", description="Bridge state")
    baud_rate: int = Field(115200, description="Serial baud rate")
    device_id: str = Field("ESP32_USB", description="Ingestion terminal ID")
    error_message: Optional[str] = Field(None, max_length=512, description="Diagnostic error details if any")

class HardwareBridgeStatusResponse(BaseModel):
    status: str
    port: str
    baud_rate: int
    last_heartbeat: Optional[str] = None
    last_event: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class HardwareTicketResponse(BaseModel):
    ticket_id: str
    uid: str
    user_name: str
    user_email: str
    status: str
    created_at: str
    expires_at: str
    expires_in_seconds: int

class HardwareStageStateResponse(BaseModel):
    state: str  # "WAITING_CONNECTION" | "CONNECTED" | "WAITING_RFID" | "RFID_ACCEPTED" | "WAITING_FINGERPRINT" | "SUCCESS" | "DENIED" | "ERROR"
    bridge_status: str  # "Connected" | "Disconnected" | "Error"
    port: str
    baud_rate: int
    latest_event: Optional[Dict[str, Any]] = None
    ticket: Optional[HardwareTicketResponse] = None
    detail: Optional[str] = None
