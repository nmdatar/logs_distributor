from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import List, Optional
import os

from .models import LogPacket, LogMessage
from .ingestor import LogIngestor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Logs Ingestor",
    description="A service for ingesting log packets and storing them in Redis queue",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ingestor
ingestor = LogIngestor(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
    queue_name=os.getenv("LOG_QUEUE_NAME", "log_queue")
)

@app.on_event("startup")
async def startup_event():
    """Initialize the ingestor on startup"""
    try:
        await ingestor.initialize()
        logger.info("Logs Ingestor started successfully")
    except Exception as e:
        logger.error(f"Failed to start Logs Ingestor: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    await ingestor.close()
    logger.info("Logs Ingestor shutdown complete")

@app.post("/logs", response_model=dict)
async def ingest_logs(packet: LogPacket):
    """
    Ingest log packets and store them in Redis queue
    """
    try:
        result = await ingestor.ingest_log_packet(packet)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "message": "Log packet ingested successfully",
            "storage_key": result["storage_key"],
            "queue_length": result["queue_length"],
            "ingested_at": result["ingested_at"]
        }
    except Exception as e:
        logger.error(f"Error ingesting log packet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs", response_model=List[dict])
async def get_logs(source: Optional[str] = None, limit: int = 100):
    """
    Retrieve stored log packets
    """
    try:
        packets = await ingestor.get_stored_packets(source=source, limit=limit)
        return packets
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/status", response_model=dict)
async def get_queue_status():
    """
    Get queue status information
    """
    try:
        queue_length = await ingestor.get_queue_length()
        return {
            "queue_name": ingestor.queue_name,
            "queue_length": queue_length,
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "logs_ingestor"}

@app.get("/")
async def root():
    """
    Root endpoint with service information
    """
    return {
        "service": "Logs Ingestor",
        "version": "1.0.0",
        "description": "Ingests log packets and stores them in Redis queue",
        "endpoints": {
            "POST /logs": "Ingest log packets",
            "GET /logs": "Retrieve stored log packets",
            "GET /queue/status": "Get queue status",
            "GET /health": "Health check"
        }
    } 