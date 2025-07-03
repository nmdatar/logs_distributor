#!/usr/bin/env python3
"""
Script to post test log packets from a JSON file to the ingestor
"""
import json
import subprocess
import time
import sys
import os

def post_packet(packet_data):
    """Post a single packet to the ingestor via curl"""
    try:
        # Convert packet to JSON string
        json_data = json.dumps(packet_data)
        
        # Build curl command
        curl_cmd = [
            "curl", "-X", "POST", 
            "http://localhost:8000/logs",
            "-H", "Content-Type: application/json",
            "-d", json_data,
            "-s"  # Silent mode
        ]
        
        # Execute curl command
        result = subprocess.run(curl_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
            
    except Exception as e:
        return False, str(e)

def load_test_data(filename):
    """Load test data from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading test data: {e}")
        return None

def main():
    # Check if ingestor is running
    try:
        result = subprocess.run(["curl", "-s", "http://localhost:8000/health"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Ingestor is not running on http://localhost:8000")
            print("Please start the ingestor first: python scripts/start_ingestor.py")
            return
    except:
        print("❌ Cannot connect to ingestor. Is it running?")
        return
    
    print("✅ Ingestor is running")
    
    # Load test data
    test_file = "tests/data/1000_messages.json"
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return
    
    packets = load_test_data(test_file)
    if not packets:
        return
    
    print(f"📦 Loaded {len(packets)} packets with {sum(len(p['messages']) for p in packets)} total messages")
    
    # Post packets
    print("\n🚀 Posting packets to ingestor...")
    successful = 0
    failed = 0
    
    for i, packet in enumerate(packets, 1):
        success, response = post_packet(packet)
        
        if success:
            successful += 1
            print(f"✅ Packet {i}/{len(packets)}: {len(packet['messages'])} messages from {packet['source']}")
        else:
            failed += 1
            print(f"❌ Packet {i}/{len(packets)}: Failed - {response}")
        
        # Small delay to avoid overwhelming the system
        time.sleep(0.1)
    
    print(f"\n📊 Results:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📦 Total packets: {len(packets)}")
    print(f"   📝 Total messages: {sum(len(p['messages']) for p in packets)}")
    
    if successful > 0:
        print(f"\n🎯 Check analyzer distribution:")
        print(f"   curl http://localhost:9001/stats")
        print(f"   curl http://localhost:9002/stats")
        print(f"   curl http://localhost:9003/stats")

if __name__ == "__main__":
    main() 