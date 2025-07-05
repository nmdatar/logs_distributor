#!/usr/bin/env python3
"""
Test script to verify message-level distribution across analyzers.
This tests that individual messages from packets are distributed based on analyzer weights.
"""

import asyncio
import httpx
import json
from datetime import datetime
import time

async def test_message_distribution():
    """Test that messages are distributed individually based on weights"""
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing Message-Level Distribution")
        print("=" * 50)
        
        # Step 1: Add analyzers with specific weights
        print("\n1. Adding analyzers...")
        
        # Analyzer 1: 60% weight
        analyzer1_data = {
            "id": "analyzer1",
            "name": "Analyzer 1 (60% weight)",
            "endpoint": "http://localhost:9001/analyze",
            "weight": 3,
            "health_check_url": "http://localhost:9001/health"
        }
        
        # Analyzer 2: 40% weight  
        analyzer2_data = {
            "id": "analyzer2", 
            "name": "Analyzer 2 (40% weight)",
            "endpoint": "http://localhost:9002/analyze",
            "weight": 2,
            "health_check_url": "http://localhost:9002/health"
        }
        
        # Add analyzers
        response = await client.post("http://localhost:8001/analyzers", json=analyzer1_data)
        print(f"✅ Added analyzer1: {response.status_code}")
        
        response = await client.post("http://localhost:8001/analyzers", json=analyzer2_data)
        print(f"✅ Added analyzer2: {response.status_code}")
        
        # Step 2: Check analyzer status
        print("\n2. Checking analyzer status...")
        response = await client.get("http://localhost:8001/analyzers")
        analyzers = response.json()
        print(f"📊 Analyzers: {json.dumps(analyzers, indent=2)}")
        
        # Step 3: Send packets with multiple messages
        print("\n3. Sending test packets...")
        
        # Packet 1: 7 messages
        packet1 = {
            "source": "test-message-distribution",
            "messages": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "message": f"Packet 1 - Message {i+1}"
                }
                for i in range(7)
            ]
        }
        
        # Packet 2: 3 messages
        packet2 = {
            "source": "test-message-distribution", 
            "messages": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "message": f"Packet 2 - Message {i+1}"
                }
                for i in range(3)
            ]
        }
        
        # Send packets
        response = await client.post("http://localhost:8000/logs", json=packet1)
        print(f"📦 Sent packet 1 (7 messages): {response.status_code}")
        
        response = await client.post("http://localhost:8000/logs", json=packet2)
        print(f"📦 Sent packet 2 (3 messages): {response.status_code}")
        
        # Step 4: Wait for processing
        print("\n4. Waiting for distribution to complete...")
        await asyncio.sleep(5)
        
        # Step 5: Check distribution statistics
        print("\n5. Checking distribution statistics...")
        response = await client.get("http://localhost:8001/analyzers/stats")
        stats = response.json()
        
        print("\n📊 Distribution Statistics:")
        print(f"Total packets processed: {stats.get('total_packets_processed', 0)}")
        print(f"Total messages distributed: {stats.get('total_messages_distributed', 0)}")
        
        analyzer_stats = stats.get('analyzers', [])
        for analyzer in analyzer_stats:
            print(f"  {analyzer['name']}: {analyzer['total_messages_processed']} messages")
        
        # Step 6: Check individual analyzer stats
        print("\n6. Checking individual analyzer statistics...")
        
        response = await client.get("http://localhost:9001/stats")
        analyzer1_stats = response.json()
        print(f"📈 Analyzer 1 stats: {json.dumps(analyzer1_stats, indent=2)}")
        
        response = await client.get("http://localhost:9002/stats")
        analyzer2_stats = response.json()
        print(f"📈 Analyzer 2 stats: {json.dumps(analyzer2_stats, indent=2)}")
        
        # Step 7: Analysis
        print("\n7. Analysis:")
        total_messages = 10  # 7 + 3
        analyzer1_messages = analyzer1_stats.get('processed_messages', 0)
        analyzer2_messages = analyzer2_stats.get('processed_messages', 0)
        
        print(f"📊 Total messages sent: {total_messages}")
        print(f"📊 Analyzer 1 received: {analyzer1_messages} messages ({analyzer1_messages/total_messages*100:.1f}%)")
        print(f"📊 Analyzer 2 received: {analyzer2_messages} messages ({analyzer2_messages/total_messages*100:.1f}%)")
        
        # Expected distribution (60/40 split)
        expected_analyzer1 = total_messages * 0.6
        expected_analyzer2 = total_messages * 0.4
        
        print(f"📊 Expected Analyzer 1: {expected_analyzer1:.1f} messages (60%)")
        print(f"📊 Expected Analyzer 2: {expected_analyzer2:.1f} messages (40%)")
        
        # Check if distribution is reasonable (within 20% of expected)
        tolerance = 0.2
        analyzer1_diff = abs(analyzer1_messages - expected_analyzer1) / expected_analyzer1
        analyzer2_diff = abs(analyzer2_messages - expected_analyzer2) / expected_analyzer2
        
        if analyzer1_diff <= tolerance and analyzer2_diff <= tolerance:
            print("✅ Distribution is working correctly!")
        else:
            print("⚠️  Distribution may not be working as expected")
            print(f"   Analyzer 1 difference: {analyzer1_diff*100:.1f}%")
            print(f"   Analyzer 2 difference: {analyzer2_diff*100:.1f}%")

if __name__ == "__main__":
    asyncio.run(test_message_distribution()) 