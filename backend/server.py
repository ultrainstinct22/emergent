from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo import MongoClient
import os
import uuid
import asyncio
from pathlib import Path
import shutil
from typing import List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URL)
db = client.video_chat_db

# Collections
videos_collection = db.videos
chats_collection = db.chats

# Create uploads directory
UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Google API key
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')

class ChatMessage(BaseModel):
    video_id: str
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    video_id: str
    session_id: str

@app.get("/")
async def root():
    return {"message": "Video Chat API"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Video Chat API is running"}

@app.post("/api/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file and return video ID"""
    try:
        # Validate file type
        if not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Generate unique video ID
        video_id = str(uuid.uuid4())
        
        # Create file path
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'mp4'
        file_path = UPLOAD_DIR / f"{video_id}.{file_extension}"
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Store video metadata in database
        video_doc = {
            "video_id": video_id,
            "filename": file.filename,
            "file_path": str(file_path),
            "content_type": file.content_type,
            "size": file_path.stat().st_size,
            "status": "uploaded",
            "analysis": None
        }
        
        videos_collection.insert_one(video_doc)
        
        logger.info(f"Video uploaded successfully: {video_id}")
        return {
            "video_id": video_id,
            "filename": file.filename,
            "status": "uploaded",
            "message": "Video uploaded successfully"
        }
        
    except Exception as e:
        logger.error(f"Error uploading video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload video: {str(e)}")

@app.post("/api/analyze-video/{video_id}")
async def analyze_video(video_id: str):
    """Analyze a video using Gemini"""
    try:
        # Check if video exists
        video_doc = videos_collection.find_one({"video_id": video_id})
        if not video_doc:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if not GOOGLE_API_KEY:
            raise HTTPException(status_code=500, detail="Google API key not configured")
        
        # Import Gemini integration
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
        except ImportError:
            raise HTTPException(status_code=500, detail="Gemini integration not available. Please install emergentintegrations library.")
        
        # Initialize Gemini chat
        chat = LlmChat(
            api_key=GOOGLE_API_KEY,
            session_id=f"analysis-{video_id}",
            system_message="You are a helpful AI assistant that analyzes videos. Provide detailed, structured analysis of video content including key topics, speakers, main points, and timestamps when possible."
        ).with_model("gemini", "gemini-2.5-pro")
        
        # Create video file reference
        video_file = FileContentWithMimeType(
            file_path=video_doc["file_path"],
            mime_type=video_doc["content_type"]
        )
        
        # Analyze video
        analysis_message = UserMessage(
            text="Please provide a comprehensive analysis of this video. Include: 1) Summary of main content, 2) Key topics discussed, 3) Important timestamps if applicable, 4) Any notable speakers or participants, 5) Overall structure of the video. Make this analysis detailed enough that I can have meaningful conversations about the video content.",
            file_contents=[video_file]
        )
        
        response = await chat.send_message(analysis_message)
        
        # Update video document with analysis
        videos_collection.update_one(
            {"video_id": video_id},
            {"$set": {"analysis": response, "status": "analyzed"}}
        )
        
        logger.info(f"Video analyzed successfully: {video_id}")
        return {
            "video_id": video_id,
            "status": "analyzed",
            "analysis": response,
            "message": "Video analyzed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing video {video_id}: {str(e)}")
        # Update video status to error
        videos_collection.update_one(
            {"video_id": video_id},
            {"$set": {"status": "error", "error": str(e)}}
        )
        raise HTTPException(status_code=500, detail=f"Failed to analyze video: {str(e)}")

@app.post("/api/chat")
async def chat_with_video(chat_request: ChatMessage):
    """Chat about a video using Gemini"""
    try:
        # Check if video exists and is analyzed
        video_doc = videos_collection.find_one({"video_id": chat_request.video_id})
        if not video_doc:
            raise HTTPException(status_code=404, detail="Video not found")
        
        if video_doc.get("status") != "analyzed":
            raise HTTPException(status_code=400, detail="Video not yet analyzed. Please analyze the video first.")
        
        if not GOOGLE_API_KEY:
            raise HTTPException(status_code=500, detail="Google API key not configured")
        
        # Import Gemini integration
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
        except ImportError:
            raise HTTPException(status_code=500, detail="Gemini integration not available")
        
        # Generate session ID if not provided
        session_id = chat_request.session_id or str(uuid.uuid4())
        
        # Initialize Gemini chat with video context
        system_message = f"""You are a helpful AI assistant that can answer questions about a specific video. 

Video Analysis:
{video_doc.get('analysis', 'No analysis available')}

Based on this video analysis, answer user questions about the video content. Be specific and reference the video content when possible. If asked about something not in the video, politely explain that the information is not available in the video."""
        
        chat = LlmChat(
            api_key=GOOGLE_API_KEY,
            session_id=f"chat-{session_id}",
            system_message=system_message
        ).with_model("gemini", "gemini-2.5-pro-preview-05-06")
        
        # Send user message
        user_message = UserMessage(text=chat_request.message)
        response = await chat.send_message(user_message)
        
        # Store chat message in database
        chat_doc = {
            "video_id": chat_request.video_id,
            "session_id": session_id,
            "user_message": chat_request.message,
            "ai_response": response,
            "timestamp": None  # MongoDB will add this
        }
        chats_collection.insert_one(chat_doc)
        
        logger.info(f"Chat completed for video {chat_request.video_id}")
        return ChatResponse(
            response=response,
            video_id=chat_request.video_id,
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"Error in chat for video {chat_request.video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat: {str(e)}")

@app.get("/api/videos")
async def get_videos():
    """Get list of uploaded videos"""
    try:
        videos = list(videos_collection.find({}, {"_id": 0}))
        return {"videos": videos}
    except Exception as e:
        logger.error(f"Error retrieving videos: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve videos")

@app.get("/api/video/{video_id}")
async def get_video(video_id: str):
    """Get video details by ID"""
    try:
        video = videos_collection.find_one({"video_id": video_id}, {"_id": 0})
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        return video
    except Exception as e:
        logger.error(f"Error retrieving video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve video")

@app.get("/api/chats/{video_id}")
async def get_chat_history(video_id: str, session_id: Optional[str] = None):
    """Get chat history for a video"""
    try:
        filter_query = {"video_id": video_id}
        if session_id:
            filter_query["session_id"] = session_id
            
        chats = list(chats_collection.find(filter_query, {"_id": 0}))
        return {"chats": chats}
    except Exception as e:
        logger.error(f"Error retrieving chats for video {video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat history")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)