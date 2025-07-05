#!/usr/bin/env python3
"""
Startup script for the Logs Distributor service
"""
import uvicorn
import os

if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("DISTRIBUTOR_HOST", "0.0.0.0")
    port = int(os.getenv("DISTRIBUTOR_PORT", "8001"))
    reload = os.getenv("DISTRIBUTOR_RELOAD", "false").lower() == "true"
    
    print(f"Starting Logs Distributor on {host}:{port}")
    print(f"Reload mode: {reload}")
    
    uvicorn.run(
        "app.distributor_app:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    ) 