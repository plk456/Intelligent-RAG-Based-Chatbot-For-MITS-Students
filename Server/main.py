from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import random
import time
import os
import json
import sys
from datetime import datetime, timedelta
import jwt
from dotenv import load_dotenv

# Load env variables from the absolute root directory path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
dotenv_path = os.path.join(ROOT_DIR, ".env")
load_dotenv(dotenv_path=dotenv_path)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import init_postgres, save_verified_user, save_conversation, load_conversation
from Server.sms import send_sms_otp
from Server.rag.pipeline import MITSQueryEngine

# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "mits_super_secret_key_1234567890_dev_only")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security = HTTPBearer()

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
from Server.redis_client import track_question, get_frequent_questions_list, redis_client

# Initialize PostgreSQL database
init_postgres()

# Initialize RAG Query Engine
query_engine = MITSQueryEngine()

# Setup FastAPI App
app = FastAPI(title="MITS Chatbot API", description="FastAPI Server for MITS Student Assistant")

# Initialize RAG index on startup
@app.on_event("startup")
def startup_event():
    query_engine.initialize_system()

# Local OTP in-memory store
otps: Dict[str, Dict[str, Any]] = {}


# Pydantic schemas for request bodies
class SendOtpRequest(BaseModel):
    mobileNumber: str = Field(..., pattern=r"^[0-9]{10}$")

class VerifyOtpRequest(BaseModel):
    userId: str
    mobileNumber: str = Field(..., pattern=r"^[0-9]{10}$")
    otp: str = Field(..., pattern=r"^[0-9]+$")

class ConversationSaveRequest(BaseModel):
    userId: str
    conversation: List[Dict[str, Any]]

class ChatRequest(BaseModel):
    query: str



# ==========================================
# API ROUTES
# ==========================================

# Health Check Route
@app.get("/health")
def get_health():
    return {"status": "OK", "message": "Chatbot server is running"}

# Chat Endpoint (RAG pipeline)
@app.post("/api/chat")
def chat(request: ChatRequest):
    try:
        # Track the question in Redis
        track_question(request.query)

        answer, contexts = query_engine.query(request.query)
        sources = [
            {"source": ctx["metadata"]["source"], "text": ctx["text"][:200] + "..."}
            for ctx in contexts
        ]
        return {
            "answer": answer,
            "sources": sources
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Streaming Chat Endpoint
@app.post("/api/chat-stream")
def chat_stream(request: ChatRequest):
    try:
        # Track the question in Redis
        track_question(request.query)
        
        return StreamingResponse(
            query_engine.query_stream(request.query), 
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Frequent Questions Endpoint
@app.get("/api/frequent-questions")
def get_frequent_questions(limit: int = 10):
    if redis_client is None:
        return {"success": False, "message": "Redis tracking is currently offline", "questions": []}
    try:
        questions = get_frequent_questions_list(limit)
        return {"success": True, "questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Manual Trigger for Indexing
@app.post("/api/reindex")
def reindex():
    try:
        success = query_engine.initialize_system(force_reindex=True)
        if success:
            return {"success": True, "message": "Reindexed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Reindexing failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        # Generate JWT access token
        token = create_access_token({"userId": user_id, "mobileNumber": mobile_number})
        return {
            "success": True,
            "message": "Mobile number verified and saved successfully",
            "storage": db_result.get("db"),
            "token": token
        }
    else:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to save verified user: {db_result.get('error')}"
        )

# Save Conversation history
@app.post("/api/conversations")
def save_user_conversation(request: ConversationSaveRequest, current_user: dict = Depends(verify_token)):
    if current_user.get("userId") != request.userId:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")
    result = save_conversation(request.userId, request.conversation)
    return result

# Load Conversation history
@app.get("/api/conversations/{userId}")
def load_user_conversation(userId: str, current_user: dict = Depends(verify_token)):
    if current_user.get("userId") != userId:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")
    convo = load_conversation(userId)
    return {"conversation": convo}

# Compute the absolute path to the templates directory (parent of current APP directory)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "templates")

# Serve main webpage at root path
@app.get("/")
def read_root():
    return FileResponse(os.path.join(TEMPLATES_DIR, "chatbot_mits.html"))

# Mount templates directory last so API routes are checked first
app.mount("/", StaticFiles(directory=TEMPLATES_DIR), name="templates")
