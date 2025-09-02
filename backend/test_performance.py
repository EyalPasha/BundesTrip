#!/usr/bin/env python3
"""
Quick Performance Test Script for BundesTrip API Optimizations
Run this before and after deploying to see the performance improvement
"""

import requests
import time
import json

# Configure this for your environment
#BASE_URL = "http://localhost:8000"  # Change to your API URL
BASE_URL = "https://api.bundestrip.com"  # For production testing

def test_endpoint(url, name):
    """Test an endpoint and measure response time"""
    print(f"\n🧪 Testing {name}...")
    
    # Test 1: First call (cache miss)
    start_time = time.time()
    try:
        response = requests.get(url, timeout=10)
        first_call_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            cache_control = response.headers.get('Cache-Control', 'None')
            print(f"  ✅ First call: {first_call_time:.3f}s (Cache: {cache_control})")
            
            # Test 2: Second call (should be cached)
            start_time = time.time()
            response2 = requests.get(url, timeout=10)
            second_call_time = time.time() - start_time
            
            if response2.status_code == 200:
                improvement = ((first_call_time - second_call_time) / first_call_time) * 100
                print(f"  🚀 Second call: {second_call_time:.3f}s")
                print(f"  📊 Improvement: {improvement:.1f}% faster")
                return True, first_call_time, second_call_time
            else:
                print(f"  ❌ Second call failed: {response2.status_code}")
        else:
            print(f"  ❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    return False, 0, 0

def main():
    print("🧪 BundesTrip API Performance Test")
    print(f"📍 Testing: {BASE_URL}")
    print("=" * 50)
    
    endpoints = [
        ("/available-cities", "Available Cities"),
        ("/available-dates", "Available Dates"),
        ("/available-leagues", "Available Leagues"),
        ("/available-teams", "Available Teams")
    ]
    
    results = []
    
    for endpoint, name in endpoints:
        url = f"{BASE_URL}{endpoint}"
        success, first_time, second_time = test_endpoint(url, name)
        if success:
            results.append((name, first_time, second_time))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE SUMMARY")
    print("=" * 50)
    
    total_first = 0
    total_second = 0
    
    for name, first_time, second_time in results:
        improvement = ((first_time - second_time) / first_time) * 100 if first_time > 0 else 0
        print(f"{name:20} | {first_time:.3f}s → {second_time:.3f}s ({improvement:.1f}% faster)")
        total_first += first_time
        total_second += second_time
    
    if results:
        overall_improvement = ((total_first - total_second) / total_first) * 100
        print("-" * 50)
        print(f"{'TOTAL':20} | {total_first:.3f}s → {total_second:.3f}s ({overall_improvement:.1f}% faster)")
        
        if overall_improvement > 80:
            print("\n🎉 EXCELLENT! Caching is working perfectly!")
        elif overall_improvement > 50:
            print("\n✅ GOOD! Significant performance improvement detected.")
        else:
            print("\n⚠️  Caching might not be working as expected.")
    
    print("\nTest completed! 🎯")

if __name__ == "__main__":
    main()
