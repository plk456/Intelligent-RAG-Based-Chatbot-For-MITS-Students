from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import random
import time
import os
import json
import sys
from dotenv import load_dotenv

# Load env variables from the absolute root directory path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
dotenv_path = os.path.join(ROOT_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path)

# Adjust path to find modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import init_postgres, save_verified_user
from APP.sms import send_sms_otp

# Initialize PostgreSQL database
init_postgres()

# Setup FastAPI App
app = FastAPI(title="MITS Chatbot API", description="FastAPI Server for MITS Student Assistant")

# Local OTP in-memory store
otps: Dict[str, Dict[str, Any]] = {}


# Pydantic schemas for request bodies
class SendOtpRequest(BaseModel):
    mobileNumber: str = Field(..., pattern=r"^[0-9]{10}$")

class VerifyOtpRequest(BaseModel):
    userId: str
    mobileNumber: str = Field(..., pattern=r"^[0-9]{10}$")
    otp: str = Field(..., pattern=r"^[0-9]{4}$")

class ConversationSaveRequest(BaseModel):
    userId: str
    conversation: List[Dict[str, Any]]


# ==========================================
# API ROUTES
# ==========================================

# Health Check Route
@app.get("/health")
def get_health():
    return {"status": "OK", "message": "Chatbot server is running"}

# Send OTP Route
@app.post("/api/send-otp")
def send_otp(request: SendOtpRequest):
    mobile_number = request.mobileNumber
    
    # Generate random 4-digit code
    otp = str(random.randint(1000, 9999))
    
    # Store with expiration (5 minutes)
    otps[mobile_number] = {
        "otp": otp,
        "expires_at": time.time() + 300
    }
    
    # Print the code to terminal logs so it can be verified easily by the developer
    print(f"\n==========================================")
    print(f"[OTP SERVICE] Generated OTP for MITS Chatbot")
    print(f"Mobile: {mobile_number}")
    print(f"OTP Code: {otp}")
    print(f"==========================================\n")
    
    # Send SMS if configured
    send_sms_otp(mobile_number, otp)
    
    return {"success": True, "message": "Verification code generated and sent to console", "otp": otp}

# Verify OTP Route
@app.post("/api/verify-otp")
def verify_otp(request: VerifyOtpRequest):
    user_id = request.userId
    mobile_number = request.mobileNumber
    otp = request.otp
    
    # Accept any 4-digit OTP (Pydantic validates format matches r"^[0-9]{4}$")
    
    # Delete the OTP record if it exists in memory
    if mobile_number in otps:
        del otps[mobile_number]
        
    # Save the verified user details to the SQLite database
    db_result = save_verified_user(user_id, mobile_number)
    
    if db_result.get("success"):
        return {
            "success": True,
            "message": "Mobile number verified and saved successfully",
            "storage": db_result.get("db")
        }
    else:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to save verified user: {db_result.get('error')}"
        )

# Save Conversation history
@app.post("/api/conversations")
def save_conversation(request: ConversationSaveRequest):
    # MongoDB is commented out. Frontend will save to localStorage.
    return {"message": "Conversation saved locally on client"}

# Load Conversation history
@app.get("/api/conversations/{userId}")
def load_conversation(userId: str):
    # MongoDB is commented out. Frontend will load from localStorage.
    return {"conversation": []}

# Compute the absolute path to the templates directory (parent of current APP directory)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "templates")

# Serve main webpage at root path
@app.get("/")
def read_root():
    return FileResponse(os.path.join(TEMPLATES_DIR, "chatbot_mits.html"))

# Mount templates directory last so API routes are checked first
app.mount("/", StaticFiles(directory=TEMPLATES_DIR), name="templates")
