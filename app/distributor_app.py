from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import asyncio
from typing import Dict
import os

from .distributor import LogDistributor
from .models import Analyzer, AnalyzerStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Logs Distributor",
    description="A service for distributing log packets from Redis queue to multiple endpoints",
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
    queue_name=os.getenv("LOG_QUEUE_NAME", "log_queue"),
    timeout=int(os.getenv("HTTP_TIMEOUT", "30"))
)

# Background task for distribution loop
distribution_task = None

@app.on_event("startup")
async def startup_event():
    """Initialize the distributor on startup"""
    try:
        await distributor.initialize()
        logger.info("Logs Distributor started successfully")
        
        # Start distribution loop in background
        global distribution_task
        distribution_task = asyncio.create_task(distributor.start_distribution_loop())
        logger.info("Distribution loop started")
    except Exception as e:
        logger.error(f"Failed to start Logs Distributor: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    global distribution_task
    
    # Stop distribution loop
    if distribution_task:
        await distributor.stop_distribution_loop()
        distribution_task.cancel()
        try:
            await distribution_task
        except asyncio.CancelledError:
            pass
    
    await distributor.close()
    logger.info("Logs Distributor shutdown complete")

@app.post("/analyzers")
async def add_analyzer(analyzer: Analyzer):
    """
    Add an analyzer with weight-based distribution
    """
    try:
        await distributor.add_analyzer(analyzer)
        return {"message": f"Analyzer {analyzer.name} added with weight {analyzer.weight}"}
    except Exception as e:
        logger.error(f"Error adding analyzer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/analyzers/{analyzer_id}")
async def remove_analyzer(analyzer_id: str):
    """
    Remove an analyzer
    """
    try:
        await distributor.remove_analyzer(analyzer_id)
        return {"message": f"Analyzer {analyzer_id} removed"}
    except Exception as e:
        logger.error(f"Error removing analyzer: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/analyzers/{analyzer_id}/status")
async def update_analyzer_status(analyzer_id: str, status: AnalyzerStatus):
    """
    Update analyzer status
    """
    try:
        await distributor.update_analyzer_status(analyzer_id, status)
        return {"message": f"Analyzer {analyzer_id} status updated to {status}"}
    except Exception as e:
        logger.error(f"Error updating analyzer status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analyzers", response_model=dict)
async def get_analyzers():
    """
    Get current analyzer configuration and status
    """
    try:
        return await distributor.get_analyzers_status()
    except Exception as e:
        logger.error(f"Error getting analyzers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analyzers/stats", response_model=dict)
async def get_analyzer_stats():
    """
    Get distribution statistics
    """
    try:
        return await distributor.get_distribution_stats()
    except Exception as e:
        logger.error(f"Error getting analyzer stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/queue/status", response_model=dict)
async def get_queue_status():
    """
    Get queue status information
    """
    try:
        queue_length = await distributor.get_queue_length()
        return {
            "queue_name": distributor.queue_name,
            "queue_length": queue_length,
            "distribution_running": distributor.running,
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/distribution/start")
async def start_distribution():
    """
    Start the distribution loop
    """
    try:
        global distribution_task
        if not distributor.running:
            distribution_task = asyncio.create_task(distributor.start_distribution_loop())
            return {"message": "Distribution loop started"}
        else:
            return {"message": "Distribution loop is already running"}
    except Exception as e:
        logger.error(f"Error starting distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/distribution/stop")
async def stop_distribution():
    """
    Stop the distribution loop
    """
    try:
        global distribution_task
        if distributor.running:
            await distributor.stop_distribution_loop()
            if distribution_task:
                distribution_task.cancel()
                try:
                    await distribution_task
                except asyncio.CancelledError:
                    pass
            return {"message": "Distribution loop stopped"}
        else:
            return {"message": "Distribution loop is not running"}
    except Exception as e:
        logger.error(f"Error stopping distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy", 
        "service": "logs_distributor",
        "distribution_running": distributor.running
    }

@app.get("/")
async def root():
    """
    Root endpoint with service information
    """
    return {
        "service": "Logs Distributor",
        "version": "1.0.0",
        "description": "Distributes log packets from Redis queue to multiple endpoints",
        "distribution_running": distributor.running,
        "endpoints": {
            "POST /analyzers": "Add analyzer with weight",
            "DELETE /analyzers/{id}": "Remove analyzer",
            "PUT /analyzers/{id}/status": "Update analyzer status",
            "GET /analyzers": "Get analyzer configuration",
            "GET /analyzers/stats": "Get distribution statistics",
            "GET /queue/status": "Get queue status",
            "POST /distribution/start": "Start distribution loop",
            "POST /distribution/stop": "Stop distribution loop",
            "GET /health": "Health check"
        }
    } 