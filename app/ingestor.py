import asyncio
import json
import logging
from typing import Optional
import redis.asyncio as redis
from datetime import datetime
from .models import LogPacket, LogMessage

logger = logging.getLogger(__name__)

class LogIngestor:
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 queue_name: str = "log_queue"):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.redis_client: Optional[redis.Redis] = None
    
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established for ingestor")
        except Exception as e:
            logger.error(f"Failed to initialize ingestor: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def ingest_log_packet(self, packet: LogPacket) -> dict:
        """Ingest a log packet and store it in Redis queue"""
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")
        
        try:
            # Add timestamp to packet for tracking
            packet_data = {
                "packet": packet.model_dump(),
                "ingested_at": datetime.now().isoformat(),
                "source": packet.source
            }
            
            # Push to Redis queue
            await self.redis_client.lpush(self.queue_name, json.dumps(packet_data))
            
            # Also store in persistent storage for retrieval
            storage_key = f"log_packet:{packet.source}:{datetime.now().isoformat()}"
            await self.redis_client.set(storage_key, json.dumps(packet_data), ex=86400)
            
            logger.info(f"Ingested log packet from {packet.source} with {len(packet.messages)} messages")
            
            return {
                "status": "success",
                "storage_key": storage_key,
                "queue_length": await self.redis_client.llen(self.queue_name),
                "ingested_at": packet_data["ingested_at"]
            }
        except Exception as e:
            logger.error(f"Failed to ingest log packet: {e}")
            return {
                "status": "error",
                "error": str(e),
                "ingested_at": datetime.now().isoformat()
            }
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        if not self.redis_client:
            return 0
        return await self.redis_client.llen(self.queue_name)
    
    async def get_stored_packets(self, source: Optional[str] = None, 
                                limit: int = 100) -> list:
        """Retrieve stored log packets from Redis"""
        if not self.redis_client:
            return []
        
        packets = []
        pattern = f"log_packet:{source or '*'}:*"
        
        async for key in self.redis_client.scan_iter(match=pattern, count=limit):
            try:
                packet_data = await self.redis_client.get(key)
                if packet_data:
                    data = json.loads(packet_data)
                    packets.append(data)
            except Exception as e:
                logger.error(f"Failed to parse packet from key {key}: {e}")
        
        return packets[:limit] 