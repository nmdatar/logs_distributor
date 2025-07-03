#!/usr/bin/env python3
"""
Test script to verify weight-based distribution accuracy.
This tests that the distributor follows the specified weights as closely as possible.
"""
import asyncio
import httpx
import json
from datetime import datetime
import time

async def test_weight_accuracy():
    """Test that distribution follows weights accurately"""
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing Weight Distribution Accuracy")
        print("=" * 50)
        
        # Step 1: Add analyzers with specific weights
        print("\n1. Adding analyzers with weights...")
        
        # Analyzer 1: 40% weight
        analyzer1_data = {
            "id": "analyzer1",
            "name": "Analyzer 1",
            "endpoint": "http://localhost:9001/analyze",
            "weight": 4.0,
            "health_check_url": "http://localhost:9001/health"
        }
        
        # Analyzer 2: 35% weight  
        analyzer2_data = {
            "id": "analyzer2",
            "name": "Analyzer 2",
            "endpoint": "http://localhost:9002/analyze",
            "weight": 3.5,
            "health_check_url": "http://localhost:9002/health"
        }
        
        # Analyzer 3: 25% weight
        analyzer3_data = {
            "id": "analyzer3",
            "name": "Analyzer 3",
            "endpoint": "http://localhost:9003/analyze",
            "weight": 2.5,
            "health_check_url": "http://localhost:9003/health"
        }
        
        # Add analyzers
        for analyzer_data in [analyzer1_data, analyzer2_data, analyzer3_data]:
            response = await client.post(
                "http://localhost:8001/analyzers",
                json=analyzer_data
            )
            if response.status_code == 200:
                print(f"✅ Added {analyzer_data['name']} with weight {analyzer_data['weight']}")
            else:
                print(f"❌ Failed to add {analyzer_data['name']}: {response.status_code}")
        
        # Step 2: Check analyzer configuration
        print("\n2. Checking analyzer configuration...")
        response = await client.get("http://localhost:8001/analyzers")
        if response.status_code == 200:
            config = response.json()
            print(f"Total weight: {config['total_weight']}")
            for analyzer in config['analyzers']:
                print(f"  {analyzer['name']}: weight {analyzer['weight']} ({analyzer['weight']/config['total_weight']*100:.1f}%)")
        
        # Step 3: Send test packets with different sizes
        print("\n3. Sending test packets...")
        
        test_cases = [
            {"name": "Small packet (5 messages)", "count": 5},
            {"name": "Medium packet (10 messages)", "count": 10},
            {"name": "Large packet (20 messages)", "count": 20},
            {"name": "Very large packet (50 messages)", "count": 50}
        ]
        
        for test_case in test_cases:
            print(f"\n📦 Testing: {test_case['name']}")
            
            # Create test packet
            messages = []
            for i in range(test_case['count']):
                messages.append({
                    "timestamp": datetime.now().isoformat(),
                    "level": "info",
                    "message": f"Test message {i+1} from {test_case['name']}"
                })
            
            packet = {
                "source": f"test_{test_case['count']}",
                "messages": messages
            }
            
            # Send packet
            response = await client.post("http://localhost:8000/logs", json=packet)
            if response.status_code == 200:
                print(f"✅ Sent {test_case['count']} messages")
                
                # Wait for processing
                await asyncio.sleep(2)
                
                # Check distribution
                await check_distribution(test_case['count'])
            else:
                print(f"❌ Failed to send packet: {response.status_code}")
        
        # Step 4: Send multiple packets to test cumulative distribution
        print("\n4. Testing cumulative distribution with multiple packets...")
        
        total_messages = 0
        for i in range(10):
            messages = []
            for j in range(5):  # 5 messages per packet
                messages.append({
                    "timestamp": datetime.now().isoformat(),
                    "level": "info",
                    "message": f"Batch message {i*5 + j + 1}"
                })
            
            packet = {
                "source": f"batch_{i}",
                "messages": messages
            }
            
            response = await client.post("http://localhost:8000/logs", json=packet)
            if response.status_code == 200:
                total_messages += 5
                print(f"✅ Sent batch {i+1}/10 (5 messages)")
                await asyncio.sleep(0.5)
            else:
                print(f"❌ Failed to send batch {i+1}: {response.status_code}")
        
        # Final distribution check
        print(f"\n📊 Final distribution check ({total_messages} total messages):")
        await check_distribution(total_messages)

async def check_distribution(expected_total):
    """Check the distribution across analyzers"""
    async with httpx.AsyncClient() as client:
        try:
            # Get stats from each analyzer
            analyzer1_stats = await client.get("http://localhost:9001/stats")
            analyzer2_stats = await client.get("http://localhost:9002/stats")
            analyzer3_stats = await client.get("http://localhost:9003/stats")
            
            if all(r.status_code == 200 for r in [analyzer1_stats, analyzer2_stats, analyzer3_stats]):
                stats1 = analyzer1_stats.json()
                stats2 = analyzer2_stats.json()
                stats3 = analyzer3_stats.json()
                
                total_received = stats1['processed_messages'] + stats2['processed_messages'] + stats3['processed_messages']
                
                print(f"  Total received: {total_received}/{expected_total}")
                print(f"  Analyzer 1: {stats1['processed_messages']} messages ({stats1['processed_messages']/total_received*100:.1f}%)")
                print(f"  Analyzer 2: {stats2['processed_messages']} messages ({stats2['processed_messages']/total_received*100:.1f}%)")
                print(f"  Analyzer 3: {stats3['processed_messages']} messages ({stats3['processed_messages']/total_received*100:.1f}%)")
                
                # Check if distribution is close to expected weights
                expected_weights = [0.4, 0.35, 0.25]  # 40%, 35%, 25%
                actual_weights = [
                    stats1['processed_messages'] / total_received,
                    stats2['processed_messages'] / total_received,
                    stats3['processed_messages'] / total_received
                ]
                
                print("  Weight accuracy:")
                for i, (expected, actual) in enumerate(zip(expected_weights, actual_weights)):
                    diff = abs(expected - actual)
                    status = "✅" if diff < 0.05 else "⚠️"  # Within 5%
                    print(f"    Analyzer {i+1}: {status} Expected {expected:.1%}, Got {actual:.1%} (diff: {diff:.1%})")
                
            else:
                print("❌ Failed to get analyzer stats")
                
        except Exception as e:
            print(f"❌ Error checking distribution: {e}")

if __name__ == "__main__":
    asyncio.run(test_weight_accuracy()) 