import asyncio
import json
import logging
import random
from typing import List, Dict, Optional, Tuple
import httpx
import redis.asyncio as redis
from datetime import datetime
from collections import defaultdict, deque
from dataclasses import dataclass
from .models import LogPacket, LogMessage, Analyzer, AnalyzerConfig, AnalyzerStatus

logger = logging.getLogger(__name__)

@dataclass
class BatchRequest:
    """Represents a batch of messages to send to an analyzer"""
    analyzer_id: str
    analyzer_endpoint: str
    messages: List[LogMessage]
    source: str

class FastLogDistributor:
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 queue_name: str = "log_queue",
                 max_concurrent_requests: int = 50,
                 batch_size: int = 100,
                 batch_timeout: float = 0.1,
                 max_retries: int = 3):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.max_concurrent_requests = max_concurrent_requests
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_retries = max_retries
        
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.running = False
        
        # Analyzer configuration
        self.analyzer_config = AnalyzerConfig(analyzers=[])
        
        # Performance tracking
        self.stats = {
            "packets_processed": 0,
            "messages_distributed": 0,
            "batches_sent": 0,
            "failed_requests": 0,
            "avg_processing_time": 0.0
        }
        
        # Batching and concurrency
        self.batch_queues: Dict[str, deque] = defaultdict(deque)
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.batch_tasks: Dict[str, asyncio.Task] = {}
        
        # Simple weight tracking (no complex fair distribution)
        self.weight_counters: Dict[str, float] = {}
    
    async def initialize(self):
        """Initialize connections with connection pooling"""
        try:
            # Redis with connection pooling
            self.redis_client = redis.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True
            )
            await self.redis_client.ping()
            
            # HTTP client with connection pooling and timeouts
            limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
            self.http_client = httpx.AsyncClient(
                limits=limits,
                timeout=httpx.Timeout(5.0, connect=1.0),
                http2=True  # Use HTTP/2 for better performance
            )
            
            logger.info("Fast distributor initialized with connection pooling")
        except Exception as e:
            logger.error(f"Failed to initialize fast distributor: {e}")
            raise
    
    async def close(self):
        """Close all connections"""
        if self.redis_client:
            await self.redis_client.close()
        if self.http_client:
            await self.http_client.aclose()
        
        # Cancel all batch tasks
        for task in self.batch_tasks.values():
            task.cancel()
    
    async def add_analyzer(self, analyzer: Analyzer):
        """Add analyzer and start batch processing task"""
        analyzer.created_at = datetime.now().isoformat()
        analyzer.updated_at = datetime.now().isoformat()
        self.analyzer_config.add_analyzer(analyzer)
        
        # Initialize weight counter
        self.weight_counters[analyzer.id] = 0.0
        
        # Start batch processing task for this analyzer
        if analyzer.id not in self.batch_tasks:
            self.batch_tasks[analyzer.id] = asyncio.create_task(
                self._batch_processor(analyzer.id, analyzer.endpoint)
            )
        
        logger.info(f"Added analyzer {analyzer.name} with weight {analyzer.weight}")
    
    async def remove_analyzer(self, analyzer_id: str):
        """Remove analyzer and stop batch processing"""
        self.analyzer_config.remove_analyzer(analyzer_id)
        
        # Cancel batch task
        if analyzer_id in self.batch_tasks:
            self.batch_tasks[analyzer_id].cancel()
            del self.batch_tasks[analyzer_id]
        
        # Clear weight counter
        self.weight_counters.pop(analyzer_id, None)
        
        logger.info(f"Removed analyzer {analyzer_id}")
    
    def _fast_distribute_messages(self, analyzers: List[Analyzer], total_messages: int) -> List[Tuple[Analyzer, int]]:
        """
        Fast distribution algorithm using simple weight tracking.
        O(n) complexity instead of O(n log n).
        """
        if not analyzers:
            return []
        
        # Simple weight-based distribution with minimal bias
        distributions = []
        remaining = total_messages
        
        for analyzer in analyzers:
            if remaining <= 0:
                distributions.append((analyzer, 0))
                continue
            
            # Get normalized weight
            normalized_weight = self.analyzer_config.get_normalized_weight(analyzer)
            
            # Calculate target messages
            target = normalized_weight * total_messages
            
            # Simple rounding with bias correction
            messages = int(target)
            if target - messages > 0.5:  # Round up if > 0.5
                messages = min(remaining, messages + 1)
            
            distributions.append((analyzer, messages))
            remaining -= messages
        
        # Distribute remaining to first analyzer (simple approach)
        if remaining > 0 and distributions:
            first_analyzer, first_count = distributions[0]
            distributions[0] = (first_analyzer, first_count + remaining)
        
        return distributions
    
    async def _batch_processor(self, analyzer_id: str, endpoint: str):
        """Background task that processes batches for an analyzer"""
        while self.running:
            try:
                # Wait for batch timeout or batch size reached
                await asyncio.sleep(self.batch_timeout)
                
                # Process all messages in batch queue
                messages = []
                sources = set()
                
                while self.batch_queues[analyzer_id] and len(messages) < self.batch_size:
                    batch_req = self.batch_queues[analyzer_id].popleft()
                    messages.extend(batch_req.messages)
                    sources.add(batch_req.source)
                
                if not messages:
                    continue
                
                # Create batch packet
                batch_packet = LogPacket(
                    source=",".join(sources),
                    messages=messages
                )
                
                # Send batch with retry logic
                success = await self._send_with_retry(endpoint, batch_packet)
                
                if success:
                    self.stats["batches_sent"] += 1
                    self.stats["messages_distributed"] += len(messages)
                    
                    # Update analyzer stats
                    for analyzer in self.analyzer_config.analyzers:
                        if analyzer.id == analyzer_id:
                            analyzer.stats.packets_processed += 1
                            analyzer.stats.messages_processed += len(messages)
                            break
                else:
                    self.stats["failed_requests"] += 1
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processor for {analyzer_id}: {e}")
                await asyncio.sleep(1)
    
    async def _send_with_retry(self, endpoint: str, packet: LogPacket) -> bool:
        """Send packet with retry logic"""
        for attempt in range(self.max_retries):
            try:
                async with self.semaphore:  # Limit concurrent requests
                    response = await self.http_client.post(
                        endpoint,
                        json=packet.model_dump(),
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        return True
                    else:
                        logger.warning(f"HTTP {response.status_code} from {endpoint}")
                        
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {endpoint}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff
        
        return False
    
    async def distribute_log_packet(self, packet: LogPacket) -> Dict[str, List[str]]:
        """Fast distribution using batching and concurrency"""
        start_time = datetime.now()
        
        results = {
            "success": [],
            "failed": [],
            "analyzers_used": []
        }
        
        # Get online analyzers
        online_analyzers = self.analyzer_config.get_online_analyzers()
        if not online_analyzers:
            return results
        
        # Fast distribution
        distributions = self._fast_distribute_messages(online_analyzers, len(packet.messages))
        
        # Add to batch queues (non-blocking)
        message_index = 0
        for analyzer, message_count in distributions:
            if message_count == 0:
                continue
            
            analyzer_messages = packet.messages[message_index:message_index + message_count]
            message_index += message_count
            
            # Add to batch queue
            batch_req = BatchRequest(
                analyzer_id=analyzer.id,
                analyzer_endpoint=analyzer.endpoint,
                messages=analyzer_messages,
                source=packet.source
            )
            
            self.batch_queues[analyzer.id].append(batch_req)
            results["analyzers_used"].append(analyzer.id)
        
        # Update stats
        processing_time = (datetime.now() - start_time).total_seconds()
        self.stats["packets_processed"] += 1
        self.stats["avg_processing_time"] = (
            (self.stats["avg_processing_time"] * (self.stats["packets_processed"] - 1) + processing_time) 
            / self.stats["packets_processed"]
        )
        
        return results
    
    async def start_distribution_loop(self):
        """High-performance distribution loop with concurrent processing"""
        self.running = True
        logger.info("Starting fast distribution loop")
        
        # Start multiple worker tasks for concurrent processing
        workers = []
        for i in range(5):  # 5 concurrent workers
            worker = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            workers.append(worker)
        
        try:
            # Wait for all workers
            await asyncio.gather(*workers)
        finally:
            # Cancel all workers
            for worker in workers:
                worker.cancel()
            
            # Wait for workers to finish
            await asyncio.gather(*workers, return_exceptions=True)
        
        logger.info("Fast distribution loop stopped")
    
    async def _worker_loop(self, worker_name: str):
        """Individual worker that processes packets concurrently"""
        while self.running:
            try:
                # Get next packet (non-blocking)
                packet_data = await self.get_next_packet()
                
                if packet_data:
                    # Process packet (non-blocking)
                    packet = LogPacket.model_validate(packet_data["packet"])
                    await self.distribute_log_packet(packet)
                else:
                    # No packets, wait a bit
                    await asyncio.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"Error in {worker_name}: {e}")
                await asyncio.sleep(0.1)
    
    async def get_next_packet(self) -> Optional[dict]:
        """Get next packet from Redis queue"""
        if not self.redis_client:
            return None
        
        try:
            packet_data = await self.redis_client.brpop(self.queue_name, timeout=0.1)
            if packet_data:
                _, data = packet_data
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting packet: {e}")
            return None
    
    async def get_stats(self) -> Dict:
        """Get performance statistics"""
        return {
            **self.stats,
            "active_batch_tasks": len(self.batch_tasks),
            "batch_queue_sizes": {k: len(v) for k, v in self.batch_queues.items()},
            "analyzers": [
                {
                    "id": analyzer.id,
                    "name": analyzer.name,
                    "weight": analyzer.weight,
                    "status": analyzer.status,
                    "stats": analyzer.stats.model_dump()
                }
                for analyzer in self.analyzer_config.analyzers
            ]
        } 