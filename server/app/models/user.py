from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum
from datetime import datetime

class UserRole(str, Enum):
    ADMIN = "admin"
    INVESTIGATOR = "investigator"
    READONLY = "readonly"

class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole = UserRole.INVESTIGATOR
    rfid: Optional[str] = None
    fingerprint_id: Optional[int] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserResponse(BaseModel):
    id: str = Field(..., alias="_id")
    email: EmailStr
    name: str
    role: UserRole
    rfid: Optional[str] = None
    fingerprint_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserLogin(BaseModel):
    email: str = Field(..., description="Username or Email address")
    password: str
    hardware_ticket_id: Optional[str] = Field(None, description="Stage 1 Hardware Authentication challenge ticket")

class HardwareAuthPayload(BaseModel):
    deviceId: str
    rfid: Optional[str] = None
    fingerprintId: Optional[int] = None
    timestamp: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
