from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import List, Optional
import os

from .models import LogPacket, LogMessage
from .distributor import LogDistributor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Logs Distributor",
    description="A service for distributing log messages to multiple endpoints",
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

# Initialize distributor
distributor = LogDistributor(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
    timeout=int(os.getenv("HTTP_TIMEOUT", "30"))
)

@app.on_event("startup")
async def startup_event():
    """Initialize the distributor on startup"""
    try:
        await distributor.initialize()
        logger.info("Logs Distributor started successfully")
    except Exception as e:
        logger.error(f"Failed to start Logs Distributor: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    await distributor.close()
    logger.info("Logs Distributor shutdown complete")

@app.post("/logs", response_model=dict)
async def receive_logs(packet: LogPacket, background_tasks: BackgroundTasks):
    """
    Receive and process log packets
    """
    try:
        # Process the log packet asynchronously
        result = await distributor.process_log_packet(packet)
        
        if result["status"] == "error":
            raise HTTPException(status_code=500, detail=result["error"])
        
        return {
            "message": "Log packet processed successfully",
            "storage_key": result["storage_key"],
            "distribution_results": result["distribution_results"]
        }
    except Exception as e:
        logger.error(f"Error processing log packet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/logs", response_model=List[LogPacket])
async def get_logs(source: Optional[str] = None, limit: int = 100):
    """
    Retrieve stored log packets
    """
    try:
        packets = await distributor.get_stored_packets(source=source, limit=limit)
        return packets
    except Exception as e:
        logger.error(f"Error retrieving logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/endpoints/{level}")
async def add_endpoint(level: str, endpoint: str):
    """
    Add an endpoint for a specific log level
    """
    try:
        await distributor.add_endpoint(level, endpoint)
        return {"message": f"Endpoint {endpoint} added for level {level}"}
    except Exception as e:
        logger.error(f"Error adding endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/endpoints/{level}")
async def remove_endpoint(level: str, endpoint: str):
    """
    Remove an endpoint for a specific log level
    """
    try:
        await distributor.remove_endpoint(level, endpoint)
        return {"message": f"Endpoint {endpoint} removed for level {level}"}
    except Exception as e:
        logger.error(f"Error removing endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/endpoints", response_model=dict)
async def get_endpoints():
    """
    Get current endpoint configuration
    """
    try:
        return await distributor.get_endpoints_status()
    except Exception as e:
        logger.error(f"Error getting endpoints: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "logs_distributor"}

@app.get("/")
async def root():
    """
    Root endpoint with service information
    """
    return {
        "service": "Logs Distributor",
        "version": "1.0.0",
        "endpoints": {
            "POST /logs": "Submit log packets for distribution",
            "GET /logs": "Retrieve stored log packets",
            "POST /endpoints/{level}": "Add endpoint for log level",
            "DELETE /endpoints/{level}": "Remove endpoint for log level",
            "GET /endpoints": "Get current endpoint configuration",
            "GET /health": "Health check"
        }
    } 