#!/usr/bin/env python3
"""
Simple Analyzer Stub for testing weight-based distribution
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
from datetime import datetime
from typing import List
import os

from .models import LogPacket, LogMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyzerStub:
    def __init__(self, analyzer_id: str, name: str, port: int):
        self.analyzer_id = analyzer_id
        self.name = name
        self.port = port
        self.processed_packets = 0
        self.processed_messages = 0
        self.start_time = datetime.now()
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title=f"Analyzer Stub - {name}",
            description=f"Test analyzer stub for {name}",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.post("/logs")
        async def receive_logs(packet: LogPacket):
            """Receive and process log packets"""
            try:
                self.processed_packets += 1
                self.processed_messages += len(packet.messages)
                
                logger.info(f"[{self.name}] Received packet from {packet.source} with {len(packet.messages)} messages")
                
                # Simulate processing time
                import asyncio
                await asyncio.sleep(0.01)  # 10ms processing time
                
                return {
                    "status": "processed",
                    "analyzer_id": self.analyzer_id,
                    "analyzer_name": self.name,
                    "packet_source": packet.source,
                    "messages_count": len(packet.messages),
                    "processed_at": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"[{self.name}] Error processing packet: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/analyze")
        async def analyze_logs(packet: LogPacket):
            """Receive and process log packets (for distributor compatibility)"""
            try:
                self.processed_packets += 1
                self.processed_messages += len(packet.messages)
                logger.info(f"[{self.name}] /analyze: Received packet from {packet.source} with {len(packet.messages)} messages")
                import asyncio
                await asyncio.sleep(0.01)
                return {
                    "status": "processed",
                    "analyzer_id": self.analyzer_id,
                    "analyzer_name": self.name,
                    "packet_source": packet.source,
                    "messages_count": len(packet.messages),
                    "processed_at": datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"[{self.name}] Error processing packet at /analyze: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "analyzer_id": self.analyzer_id,
                "analyzer_name": self.name,
                "uptime": str(datetime.now() - self.start_time),
                "processed_packets": self.processed_packets,
                "processed_messages": self.processed_messages
            }
        
        @self.app.get("/stats")
        async def get_stats():
            """Get analyzer statistics"""
            return {
                "analyzer_id": self.analyzer_id,
                "analyzer_name": self.name,
                "start_time": self.start_time.isoformat(),
                "uptime": str(datetime.now() - self.start_time),
                "processed_packets": self.processed_packets,
                "processed_messages": self.processed_messages,
                "messages_per_second": self.processed_messages / max((datetime.now() - self.start_time).total_seconds(), 1)
            }
        
        @self.app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "service": f"Analyzer Stub - {self.name}",
                "analyzer_id": self.analyzer_id,
                "port": self.port,
                "endpoints": {
                    "POST /logs": "Receive log packets",
                    "GET /health": "Health check",
                    "GET /stats": "Get statistics"
                }
            }

def create_analyzer_stub(analyzer_id: str, name: str, port: int) -> FastAPI:
    """Create an analyzer stub FastAPI application"""
    stub = AnalyzerStub(analyzer_id, name, port)
    return stub.app 