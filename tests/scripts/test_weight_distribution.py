#!/usr/bin/env python3
"""
Test script to demonstrate weight-based distribution
"""
import asyncio
import httpx
import time
import json
from datetime import datetime
from app.models import LogPacket, LogMessage

async def test_weight_distribution():
    """Test weight-based distribution with multiple analyzers"""
    
    ingestor_url = "http://localhost:8000"
    distributor_url = "http://localhost:8001"
    
    print("🧪 Testing Weight-Based Distribution")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # 1. Setup analyzers with different weights
        print("\n1. Setting up analyzers with weights...")
        analyzers = [
            {
                "id": "analyzer-1",
                "name": "Fast Analyzer (40%)",
                "endpoint": "http://localhost:8081/logs",
                "weight": 0.4,
                "health_check_url": "http://localhost:8081/health"
            },
            {
                "id": "analyzer-2", 
                "name": "Medium Analyzer (30%)",
                "endpoint": "http://localhost:8082/logs",
                "weight": 0.3,
                "health_check_url": "http://localhost:8082/health"
            },
            {
                "id": "analyzer-3",
                "name": "Slow Analyzer (20%)", 
                "endpoint": "http://localhost:8083/logs",
                "weight": 0.2,
                "health_check_url": "http://localhost:8083/health"
            },
            {
                "id": "analyzer-4",
                "name": "Backup Analyzer (10%)",
                "endpoint": "http://localhost:8084/logs", 
                "weight": 0.1,
                "health_check_url": "http://localhost:8084/health"
            }
        ]
        
        for analyzer in analyzers:
            try:
                await client.post(f"{distributor_url}/analyzers", json=analyzer)
                print(f"✅ Added {analyzer['name']} with weight {analyzer['weight']}")
            except Exception as e:
                print(f"❌ Failed to add {analyzer['name']}: {e}")
        
        # 2. Send multiple log packets
        print(f"\n2. Sending log packets for distribution testing...")
        num_packets = 100
        
        for i in range(num_packets):
            messages = [
                LogMessage(
                    timestamp=datetime.now().isoformat(),
                    level="INFO",
                    message=f"Test message {i} - {j}"
                )
                for j in range(3)  # 3 messages per packet
            ]
            
            packet = LogPacket(
                source=f"test-source-{i % 5}",  # 5 different sources
                messages=messages
            )
            
            try:
                response = await client.post(f"{ingestor_url}/logs", json=packet.model_dump())
                if i % 20 == 0:  # Progress indicator
                    print(f"   Sent packet {i+1}/{num_packets}")
            except Exception as e:
                print(f"❌ Failed to send packet {i}: {e}")
        
        # 3. Wait for distribution to complete
        print(f"\n3. Waiting for distribution to complete...")
        await asyncio.sleep(5)
        
        # 4. Get distribution statistics
        print(f"\n4. Distribution Statistics:")
        try:
            stats_response = await client.get(f"{distributor_url}/analyzers/stats")
            stats = stats_response.json()
            
            print(f"   Total packets processed: {stats['total_packets_processed']}")
            print(f"   Total messages distributed: {stats['total_messages_distributed']}")
            print(f"   Failed distributions: {stats['failed_distributions']}")
            
            print(f"\n   Analyzer Distribution:")
            for analyzer in stats['analyzers']:
                percentage = (analyzer['total_messages_processed'] / max(stats['total_messages_distributed'], 1)) * 100
                print(f"   - {analyzer['name']}: {analyzer['total_messages_processed']} messages ({percentage:.1f}%)")
                
        except Exception as e:
            print(f"❌ Failed to get stats: {e}")
        
        # 5. Test analyzer offline scenario
        print(f"\n5. Testing analyzer offline scenario...")
        try:
            # Mark one analyzer as offline
            await client.put(f"{distributor_url}/analyzers/analyzer-4/status", json="offline")
            print("   ✅ Marked analyzer-4 as offline")
            
            # Send more packets
            print("   Sending additional packets...")
            for i in range(20):
                messages = [
                    LogMessage(
                        timestamp=datetime.now().isoformat(),
                        level="INFO",
                        message=f"Post-offline message {i}"
                    )
                ]
                
                packet = LogPacket(
                    source="offline-test",
                    messages=messages
                )
                
                await client.post(f"{ingestor_url}/logs", json=packet.model_dump())
            
            # Wait and check stats again
            await asyncio.sleep(3)
            
            stats_response = await client.get(f"{distributor_url}/analyzers/stats")
            stats = stats_response.json()
            
            print(f"   Post-offline distribution:")
            for analyzer in stats['analyzers']:
                if analyzer['status'] == 'online':
                    percentage = (analyzer['total_messages_processed'] / max(stats['total_messages_distributed'], 1)) * 100
                    print(f"   - {analyzer['name']}: {analyzer['total_messages_processed']} messages ({percentage:.1f}%)")
                else:
                    print(f"   - {analyzer['name']}: OFFLINE")
                    
        except Exception as e:
            print(f"❌ Failed to test offline scenario: {e}")
        
        # 6. Test analyzer recovery
        print(f"\n6. Testing analyzer recovery...")
        try:
            # Bring analyzer back online
            await client.put(f"{distributor_url}/analyzers/analyzer-4/status", json="online")
            print("   ✅ Brought analyzer-4 back online")
            
            # Send final packets
            print("   Sending final test packets...")
            for i in range(10):
                messages = [
                    LogMessage(
                        timestamp=datetime.now().isoformat(),
                        level="INFO",
                        message=f"Recovery test message {i}"
                    )
                ]
                
                packet = LogPacket(
                    source="recovery-test",
                    messages=messages
                )
                
                await client.post(f"{ingestor_url}/logs", json=packet.model_dump())
            
            # Final stats
            await asyncio.sleep(2)
            stats_response = await client.get(f"{distributor_url}/analyzers/stats")
            stats = stats_response.json()
            
            print(f"   Final distribution:")
            for analyzer in stats['analyzers']:
                percentage = (analyzer['total_messages_processed'] / max(stats['total_messages_distributed'], 1)) * 100
                print(f"   - {analyzer['name']}: {analyzer['total_messages_processed']} messages ({percentage:.1f}%)")
                
        except Exception as e:
            print(f"❌ Failed to test recovery: {e}")

if __name__ == "__main__":
    print("Weight-Based Distribution Test")
    print("Make sure all services are running:")
    print("  - Ingestor: python scripts/start_ingestor.py")
    print("  - Distributor: python scripts/start_distributor.py")
    print("  - Analyzer stubs:")
    print("    python scripts/start_analyzer_stub.py --id analyzer-1 --name 'Fast Analyzer' --port 8081")
    print("    python scripts/start_analyzer_stub.py --id analyzer-2 --name 'Medium Analyzer' --port 8082")
    print("    python scripts/start_analyzer_stub.py --id analyzer-3 --name 'Slow Analyzer' --port 8083")
    print("    python scripts/start_analyzer_stub.py --id analyzer-4 --name 'Backup Analyzer' --port 8084")
    print()
    
    try:
        asyncio.run(test_weight_distribution())
        print("\n🎉 Weight-based distribution test completed!")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Make sure all services are running and Redis is available") 