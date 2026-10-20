import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.core.database import get_database
from app.core.config import settings

router = APIRouter(tags=["settings"])

class SettingsUpdate(BaseModel):
    simulation_mode: bool
    gemini_api_key: Optional[str] = None
    upload_dir: Optional[str] = None

# In-memory backup in case MongoDB is initializing or we want immediate global access
_global_settings_cache = {
    "simulation_mode": settings.SIMULATION_MODE,
    "gemini_api_key": settings.GEMINI_API_KEY,
    "upload_dir": settings.UPLOAD_DIR
}

def get_current_simulation_mode() -> bool:
    return _global_settings_cache["simulation_mode"]

def get_gemini_key() -> str:
    return _global_settings_cache["gemini_api_key"] or settings.GEMINI_API_KEY

async def sync_settings_from_db():
    """Load settings stored in MongoDB into the in-memory cache."""
    try:
        db = get_database()
        doc = await asyncio.wait_for(db["settings"].find_one({"key": "global_config"}), timeout=3.0)
        if doc:
            if "simulation_mode" in doc:
                _global_settings_cache["simulation_mode"] = bool(doc["simulation_mode"])
            if "gemini_api_key" in doc:
                _global_settings_cache["gemini_api_key"] = doc["gemini_api_key"]
            if "upload_dir" in doc:
                _global_settings_cache["upload_dir"] = doc["upload_dir"]
    except Exception as e:
        print(f"Warning: Could not sync settings from DB: {e}")

@router.get("/settings")
async def get_settings():
    try:
        db = get_database()
        doc = await asyncio.wait_for(db["settings"].find_one({"key": "global_config"}), timeout=3.0)
    except Exception as e:
        print(f"[SETTINGS_FALLBACK] Database offline or timed out: {e}")
        return _global_settings_cache
    
    if not doc:
        # Return default loaded from config/env
        return _global_settings_cache
    
    sim_mode = doc.get("simulation_mode", _global_settings_cache["simulation_mode"])
    gemini_key = doc.get("gemini_api_key", _global_settings_cache["gemini_api_key"])
    upload_dir = doc.get("upload_dir", _global_settings_cache["upload_dir"])

    _global_settings_cache["simulation_mode"] = sim_mode
    _global_settings_cache["gemini_api_key"] = gemini_key
    _global_settings_cache["upload_dir"] = upload_dir

    return {
        "simulation_mode": sim_mode,
        "gemini_api_key": gemini_key,
        "upload_dir": upload_dir
    }

@router.post("/settings")
async def update_settings(payload: Dict[str, Any]):
    db = get_database()
    
    # Extract keys
    simulation_mode = payload.get("simulation_mode")
    gemini_key = payload.get("gemini_api_key")
    upload_dir = payload.get("upload_dir")
    
    update_doc: Dict[str, Any] = {}
    if simulation_mode is not None:
        update_doc["simulation_mode"] = bool(simulation_mode)
        _global_settings_cache["simulation_mode"] = bool(simulation_mode)
        
    if gemini_key is not None:
        update_doc["gemini_api_key"] = gemini_key
        _global_settings_cache["gemini_api_key"] = gemini_key
        
    if upload_dir is not None:
        update_doc["upload_dir"] = upload_dir
        _global_settings_cache["upload_dir"] = upload_dir

    await db["settings"].update_one(
        {"key": "global_config"},
        {"$set": update_doc},
        upsert=True
    )
    
    return {"success": True, "settings": _global_settings_cache}

@router.get("/settings/diagnostics")
async def get_system_diagnostics():
    import time
    import os
    
    start_time = time.time()
    db_status = "ONLINE"
    db_latency_ms = 0
    try:
        db = get_database()
        await db.command("ping")
        db_latency_ms = round((time.time() - start_time) * 1000, 1)
    except Exception as e:
        db_status = f"ERROR: {str(e)}"
        
    upload_path = _global_settings_cache.get("upload_dir") or "./evidence_vault"
    storage_accessible = os.path.exists(upload_path) or os.access(".", os.W_OK)
    
    gemini_key = _global_settings_cache.get("gemini_api_key") or ""
    masked_key = ""
    if gemini_key:
        masked_key = gemini_key[:6] + "..." + gemini_key[-4:] if len(gemini_key) > 10 else "********"
        
    return {
        "database": {
            "status": db_status,
            "latency_ms": db_latency_ms,
            "engine": "MongoDB Replica/Standalone"
        },
        "storage": {
            "path": upload_path,
            "accessible": storage_accessible,
            "status": "OPERATIONAL" if storage_accessible else "DEGRADED"
        },
        "ai_engine": {
            "key_configured": bool(gemini_key),
            "masked_key": masked_key,
            "mode": "GEMINI_CLOUD" if gemini_key else "DETERMINISTIC_OFFLINE"
        },
        "hardware_simulation": {
            "enabled": _global_settings_cache.get("simulation_mode", True),
            "status": "ONLINE"
        },
        "server_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

class TestKeyPayload(BaseModel):
    gemini_api_key: str

@router.post("/settings/test-key")
async def test_gemini_key(payload: TestKeyPayload):
    key = payload.gemini_api_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="API Key cannot be empty.")
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        # Test model listing or light query
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        resp = model.generate_content("Ping")
        return {
            "valid": True,
            "message": "Google Gemini API Key authenticated successfully. Forensic threat intelligence engine ready.",
            "test_response": resp.text[:50] if resp and resp.text else "OK"
        }
    except Exception as e:
        err_msg = str(e)
        if "API_KEY_INVALID" in err_msg or "400" in err_msg:
            raise HTTPException(status_code=400, detail="Google Gemini rejected this API Key. Please verify the key from Google AI Studio.")
        return {
            "valid": False,
            "message": f"Connection check: {err_msg[:120]}"
        }

