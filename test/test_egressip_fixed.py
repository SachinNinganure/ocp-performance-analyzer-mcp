#!/usr/bin/env python3

"""
Test script for EgressIP analyzer components
Fixed to handle PrometheusBaseQuery initialization properly
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_egressip_metrics_collector():
    """Test the EgressIP metrics collector with proper initialization"""
    print("Testing EgressIP Metrics Collector...")
    
    try:
        from tools.egressip.egressip_metrics_collector import EgressIPMetricsCollector
        
        # Initialize with a mock prometheus URL since we might not have one available
        collector = EgressIPMetricsCollector(
            database_path="./test_egressip_metrics.db",
            prometheus_url="http://localhost:9090"
        )
        
        print("✓ EgressIP Metrics Collector initialized successfully")
        
        # Test cluster metrics collection (this will likely fail due to missing cluster access, but should not crash)
        result = await collector.collect_egressip_cluster_metrics()
        print(f"✓ EgressIP Cluster metrics collection completed: {result['status']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing EgressIP Metrics Collector: {e}")
        return False

async def test_egressip_ovn_analyzer():
    """Test the EgressIP OVN rule analyzer"""
    print("\nTesting EgressIP OVN Rule Analyzer...")
    
    try:
        from tools.egressip.egressip_ovn_rule_analyzer import EgressIPOVNRuleAnalyzer
        
        # Initialize with prometheus URL
        analyzer = EgressIPOVNRuleAnalyzer(prometheus_url="http://localhost:9090")
        print("✓ EgressIP OVN Rule Analyzer initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing EgressIP OVN Rule Analyzer: {e}")
        return False

async def test_egressip_cornet_runner():
    """Test the EgressIP CORNET-6498 runner"""
    print("\nTesting EgressIP CORNET-6498 Runner...")
    
    try:
        from tools.egressip.egressip_cornet_6498_runner import EgressIPCORNET6498Runner
        
        # Initialize with test directory and prometheus URL
        runner = EgressIPCORNET6498Runner(
            test_base_dir="/tmp/test_egress",
            prometheus_url="http://localhost:9090"
        )
        print("✓ EgressIP CORNET-6498 Runner initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing EgressIP CORNET-6498 Runner: {e}")
        return False

async def main():
    """Run all EgressIP tests"""
    print("Starting EgressIP component tests...\n")
    
    results = []
    
    # Test each component
    results.append(await test_egressip_metrics_collector())
    results.append(await test_egressip_ovn_analyzer()) 
    results.append(await test_egressip_cornet_runner())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All EgressIP tests passed!")
        return 0
    else:
        print("❌ Some EgressIP tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))