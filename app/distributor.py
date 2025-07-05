import asyncio
import json
import logging
import random
from typing import List, Dict, Optional
import httpx
import redis.asyncio as redis
from datetime import datetime
from .models import LogPacket, LogMessage, Analyzer, AnalyzerConfig, AnalyzerStatus

logger = logging.getLogger(__name__)

class LogDistributor:
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 queue_name: str = "log_queue",
                 max_retries: int = 3, timeout: int = 30,
                 health_check_interval: int = 30):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.max_retries = max_retries
        self.timeout = timeout
        self.health_check_interval = health_check_interval
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.running = False
        
        # Analyzer configuration with weight-based distribution
        self.analyzer_config = AnalyzerConfig(analyzers=[])
        
        # Distribution statistics
        self.distribution_stats = {
            "total_packets_processed": 0,
            "total_messages_distributed": 0,
            "failed_distributions": 0
        }
    
    async def initialize(self):
        """Initialize Redis connection and HTTP client"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            self.http_client = httpx.AsyncClient(timeout=self.timeout)
            logger.info("HTTP client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize distributor: {e}")
            raise
    
    async def close(self):
        """Close connections"""
        if self.redis_client:
            await self.redis_client.close()
        if self.http_client:
            await self.http_client.aclose()
    
    async def add_analyzer(self, analyzer: Analyzer):
        """Add an analyzer with weight-based distribution"""
        analyzer.created_at = datetime.now().isoformat()
        analyzer.updated_at = datetime.now().isoformat()
        self.analyzer_config.add_analyzer(analyzer)
        logger.info(f"Added analyzer {analyzer.name} with weight {analyzer.weight}")
    
    async def remove_analyzer(self, analyzer_id: str):
        """Remove an analyzer"""
        self.analyzer_config.remove_analyzer(analyzer_id)
        logger.info(f"Removed analyzer {analyzer_id}")
    
    async def update_analyzer_status(self, analyzer_id: str, status: AnalyzerStatus):
        """Update analyzer status and recalculate weights"""
        for analyzer in self.analyzer_config.analyzers:
            if analyzer.id == analyzer_id:
                analyzer.status = status
                analyzer.updated_at = datetime.now().isoformat()
                logger.info(f"Updated analyzer {analyzer_id} status to {status}")
                break
        
        # Recalculate weights when status changes
        self.analyzer_config._recalculate_weights()
    
    async def check_analyzer_health(self, analyzer: Analyzer) -> bool:
        """Check if analyzer is healthy"""
        if not analyzer.health_check_url:
            return True  # Assume healthy if no health check URL
        
        try:
            response = await self.http_client.get(analyzer.health_check_url, timeout=5)
            analyzer.last_health_check = datetime.now().isoformat()
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed for analyzer {analyzer.id}: {e}")
            return False
    
    async def health_check_loop(self):
        """Background loop to check analyzer health"""
        while self.running:
            try:
                for analyzer in self.analyzer_config.analyzers:
                    is_healthy = await self.check_analyzer_health(analyzer)
                    new_status = AnalyzerStatus.ONLINE if is_healthy else AnalyzerStatus.OFFLINE
                    
                    if analyzer.status != new_status:
                        await self.update_analyzer_status(analyzer.id, new_status)
                
                await asyncio.sleep(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def get_next_packet(self) -> Optional[dict]:
        """Get next log packet from Redis queue"""
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")
        
        try:
            # Pop from right side of queue (FIFO)
            packet_data = await self.redis_client.brpop(self.queue_name, timeout=1)
            if packet_data:
                _, data = packet_data
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting packet from queue: {e}")
            return None
    
    def select_analyzer_by_weight(self) -> Optional[Analyzer]:
        """Select an analyzer based on weight distribution"""
        online_analyzers = self.analyzer_config.get_online_analyzers()
        if not online_analyzers:
            return None
        
        # Use weighted random selection
        weights = [analyzer.weight for analyzer in online_analyzers]
        selected_analyzer = random.choices(online_analyzers, weights=weights, k=1)[0]
        return selected_analyzer
    
    async def distribute_log_packet(self, packet: LogPacket) -> Dict[str, List[str]]:
        """Distribute individual messages from log packet to analyzers based on weight distribution"""
        if not self.http_client:
            raise RuntimeError("HTTP client not initialized")
        
        results = {
            "success": [],
            "failed": [],
            "analyzers_used": []
        }
        
        # Get online analyzers
        online_analyzers = self.analyzer_config.get_online_analyzers()
        if not online_analyzers:
            logger.warning("No online analyzers available")
            return results
        
        total_messages = len(packet.messages)
        if total_messages == 0:
            logger.warning("Empty log packet received")
            return results
        
        # Use fair distribution algorithm that tracks cumulative distribution
        analyzer_distributions = self._fair_distribute_messages(online_analyzers, total_messages)

        # DEBUG: Log the planned distribution
        logger.info(f"Planned analyzer distribution: " + ", ".join([f"{a.name}: {count}" for a, count in analyzer_distributions]))

        # Create and send packets to each analyzer
        message_index = 0
        packets_sent = 0  # Track total packets sent across all analyzers
        
        for analyzer, message_count in analyzer_distributions:
            if message_count == 0:
                continue
                
            # Extract messages for this analyzer
            analyzer_messages = packet.messages[message_index:message_index + message_count]
            message_index += message_count
            
            # Create a new packet for this analyzer
            analyzer_packet = LogPacket(
                source=packet.source,
                messages=analyzer_messages
            )
            
            try:
                # Send to analyzer
                response = await self.http_client.post(
                    analyzer.endpoint,
                    json=analyzer_packet.model_dump(),
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    logger.info(f"Successfully sent {len(analyzer_messages)} messages to {analyzer.name}")
                    results["success"].append(f"{analyzer.name}: {len(analyzer_messages)} messages")
                    results["analyzers_used"].append(analyzer.id)
                    
                    # Update analyzer stats - only increment packets_processed once per original packet
                    packets_sent += 1
                    analyzer.stats.messages_processed += len(analyzer_messages)
                else:
                    logger.error(f"Failed to send to {analyzer.name}: HTTP {response.status_code}")
                    results["failed"].append(f"{analyzer.name}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Error sending to {analyzer.name}: {str(e)}")
                results["failed"].append(f"{analyzer.name}: {str(e)}")
        
        # Update packets_processed only once per original packet, distributed proportionally
        if packets_sent > 0:
            for analyzer in online_analyzers:
                if analyzer.id in results["analyzers_used"]:
                    # Distribute the packet count proportionally based on weight
                    normalized_weight = self.analyzer_config.get_normalized_weight(analyzer)
                    analyzer.stats.packets_processed += normalized_weight
        
        return results
    
    def _fair_distribute_messages(self, analyzers: List[Analyzer], total_messages: int) -> List[tuple]:
        """
        Fair weight-based distribution that tracks cumulative distribution to ensure fairness over time.
        Uses a cumulative tracking approach to minimize bias.
        """
        if not analyzers:
            return []
        
        # Initialize cumulative distribution tracking if not exists
        if not hasattr(self, '_cumulative_distribution'):
            self._cumulative_distribution = {analyzer.id: 0.0 for analyzer in analyzers}
        
        # Calculate target messages for each analyzer
        target_distributions = []
        for analyzer in analyzers:
            normalized_weight = self.analyzer_config.get_normalized_weight(analyzer)
            target_messages = normalized_weight * total_messages
            target_distributions.append((analyzer, target_messages))
        
        # DEBUG: Log target calculations
        logger.info(f"DEBUG: Total messages={total_messages}, targets: " + ", ".join([f"{a.name}={t:.3f}" for a, t in target_distributions]))
        
        # Distribute messages using cumulative tracking
        distributions = [(analyzer, 0) for analyzer, _ in target_distributions]
        
        for message_idx in range(total_messages):
            # Find analyzer with lowest cumulative distribution relative to target
            best_analyzer_idx = 0
            best_ratio = float('inf')
            
            for idx, (analyzer, target_messages) in enumerate(target_distributions):
                if target_messages <= 0:
                    continue
                    
                current_count = distributions[idx][1]
                cumulative = self._cumulative_distribution[analyzer.id]
                
                # Calculate how far behind this analyzer is from its target
                target_ratio = (cumulative + current_count) / target_messages
                
                if target_ratio < best_ratio:
                    best_ratio = target_ratio
                    best_analyzer_idx = idx
            
            # Assign message to best analyzer
            analyzer, current_count = distributions[best_analyzer_idx]
            distributions[best_analyzer_idx] = (analyzer, current_count + 1)
            
            # Update cumulative distribution
            self._cumulative_distribution[analyzer.id] += 1
            
            logger.info(f"DEBUG: Message {message_idx + 1} assigned to {analyzer.name}, cumulative={self._cumulative_distribution[analyzer.id]:.2f}")
        
        # DEBUG: Log final distribution
        logger.info(f"DEBUG: Final distribution: " + ", ".join([f"{a.name}={count}" for a, count in distributions]))
        
        return distributions
    
    async def process_log_packet(self, packet_data: dict) -> Dict[str, any]:
        """Process a log packet from queue: distribute to analyzers"""
        try:
            # Extract packet from queue data
            packet = LogPacket.model_validate(packet_data["packet"])
            
            # Distribute to analyzers
            distribution_results = await self.distribute_log_packet(packet)
            
            # Update statistics
            self.distribution_stats["total_packets_processed"] += 1
            
            return {
                "status": "success",
                "source": packet.source,
                "distribution_results": distribution_results,
                "processed_at": datetime.now().isoformat(),
                "ingested_at": packet_data.get("ingested_at")
            }
        except Exception as e:
            logger.error(f"Failed to process log packet: {e}")
            self.distribution_stats["failed_distributions"] += 1
            return {
                "status": "error",
                "error": str(e),
                "processed_at": datetime.now().isoformat()
            }
    
    async def get_stored_packets(self, source: Optional[str] = None, 
                                limit: int = 100) -> List[LogPacket]:
        """Retrieve stored log packets from Redis"""
        if not self.redis_client:
            raise RuntimeError("Redis client not initialized")
        
        packets = []
        pattern = f"log_packet:{source or '*'}:*"
        
        async for key in self.redis_client.scan_iter(match=pattern, count=limit):
            try:
                packet_data = await self.redis_client.get(key)
                if packet_data:
                    packet = LogPacket.model_validate_json(packet_data)
                    packets.append(packet)
            except Exception as e:
                logger.error(f"Failed to parse packet from key {key}: {e}")
        
        return packets[:limit]
    
    async def get_analyzers_status(self) -> Dict:
        """Get current analyzer configuration and status"""
        return {
            "analyzers": [analyzer.model_dump() for analyzer in self.analyzer_config.analyzers],
            "total_weight": self.analyzer_config.total_weight,
            "online_count": len(self.analyzer_config.get_online_analyzers()),
            "total_count": len(self.analyzer_config.analyzers)
        }
    
    async def get_distribution_stats(self) -> Dict:
        """Get distribution statistics"""
        return {
            **self.distribution_stats,
            "analyzers": [
                {
                    "id": analyzer.id,
                    "name": analyzer.name,
                    "weight": analyzer.weight,
                    "status": analyzer.status,
                    "total_messages_processed": analyzer.total_messages_processed
                }
                for analyzer in self.analyzer_config.analyzers
            ]
        }
    
    async def start_distribution_loop(self):
        """Start the main distribution loop with health checks"""
        self.running = True
        logger.info("Starting distribution loop")
        
        # Start health check loop in background
        health_check_task = asyncio.create_task(self.health_check_loop())
        
        try:
            while self.running:
                try:
                    # Get next packet from queue
                    packet_data = await self.get_next_packet()
                    
                    if packet_data:
                        # Process the packet
                        result = await self.process_log_packet(packet_data)
                        
                        if result["status"] == "success":
                            logger.info(f"Distributed packet from {result['source']}")
                        else:
                            logger.error(f"Failed to distribute packet: {result['error']}")
                    else:
                        # No packets in queue, wait a bit
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Error in distribution loop: {e}")
                    await asyncio.sleep(1)  # Wait before retrying
        finally:
            # Cancel health check task
            health_check_task.cancel()
            try:
                await health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Distribution loop stopped")
    
    async def stop_distribution_loop(self):
        """Stop the distribution loop"""
        self.running = False
        logger.info("Stopping distribution loop")
    
    async def get_queue_length(self) -> int:
        """Get current queue length"""
        if not self.redis_client:
            return 0
        return await self.redis_client.llen(self.queue_name) 