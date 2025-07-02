#!/usr/bin/env python3
"""
Startup script for the Logs Ingestor service
"""
import uvicorn
import os

if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("INGESTOR_HOST", "0.0.0.0")
    port = int(os.getenv("INGESTOR_PORT", "8000"))
    reload = os.getenv("INGESTOR_RELOAD", "false").lower() == "true"
    
    print(f"Starting Logs Ingestor on {host}:{port}")
    print(f"Reload mode: {reload}")
    
    uvicorn.run(
        "app.ingestor_app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    ) 