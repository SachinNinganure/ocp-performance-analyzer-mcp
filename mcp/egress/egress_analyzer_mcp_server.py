#!/usr/bin/env python3
"""
OpenShift EgressIP Performance Analyzer MCP Server

This server provides AI-powered analysis and testing capabilities for OpenShift EgressIP functionality,
including large-scale performance testing, OVN rule validation, and automated bottleneck detection.

Author: Performance Scale Team
License: Apache-2.0
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("EgressIP Performance Analyzer")

class EgressIPAnalyzer:
    """Core EgressIP analysis and testing functionality"""
    
    def __init__(self, kubeconfig_path: Optional[str] = None):
        self.kubeconfig_path = kubeconfig_path or os.getenv('KUBECONFIG')
        self.test_results_dir = Path("./test_results")
        self.test_results_dir.mkdir(exist_ok=True)
        
    async def run_corenet_6498_test(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute CORENET-6498 large-scale EgressIP stress test"""
        try:
            logger.info("Starting CORENET-6498 test execution")
            
            # Prepare test configuration
            test_config = {
                "eip_object_count": config.get("eip_object_count", 10),
                "pods_per_eip": config.get("pods_per_eip", 200),
                "iterations": config.get("iterations", 20),
                "ip_stack": config.get("ip_stack", "auto"),
                "platform": config.get("platform", "auto")
            }
            
            # Execute Go test via wrapper
            result = await self._execute_go_test("cornet_6498_test.go", test_config)
            
            # Analyze test results
            analysis = await self._analyze_test_results(result)
            
            return {
                "status": "success",
                "test_config": test_config,
                "execution_time": result.get("execution_time"),
                "test_results": result.get("results", {}),
                "analysis": analysis,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error executing CORNET-6498 test: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def validate_snat_lrp_rules(self, node_name: str) -> Dict[str, Any]:
        """Validate SNAT/LRP rules consistency on specific node"""
        try:
            logger.info(f"Validating SNAT/LRP rules on node: {node_name}")
            
            # Get SNAT rules
            snat_rules = await self._get_ovn_snat_rules(node_name)
            
            # Get LRP rules
            lrp_rules = await self._get_ovn_lrp_rules(node_name)
            
            # Get EgressIP objects and their assignments
            egressip_assignments = await self._get_egressip_assignments()
            
            # Validate rule consistency
            validation_results = await self._validate_rule_consistency(
                snat_rules, lrp_rules, egressip_assignments
            )
            
            return {
                "status": "success",
                "node_name": node_name,
                "snat_rules_count": len(snat_rules),
                "lrp_rules_count": len(lrp_rules),
                "egressip_count": len(egressip_assignments),
                "validation_results": validation_results,
                "rules_details": {
                    "snat_rules": snat_rules[:10],  # First 10 for brevity
                    "lrp_rules": lrp_rules[:10]
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error validating SNAT/LRP rules: {e}")
            return {
                "status": "error",
                "error": str(e),
                "node_name": node_name,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def analyze_egressip_performance(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Analyze EgressIP performance metrics and identify bottlenecks"""
        try:
            logger.info(f"Analyzing EgressIP performance for namespace: {namespace or 'all'}")
            
            # Get EgressIP objects
            egressips = await self._get_egressip_objects(namespace)
            
            # Get pod assignments and traffic patterns
            pod_assignments = await self._get_pod_egressip_assignments(namespace)
            
            # Get node resource utilization
            node_metrics = await self._get_node_metrics()
            
            # Analyze performance patterns
            performance_analysis = await self._analyze_performance_patterns(
                egressips, pod_assignments, node_metrics
            )
            
            # Identify bottlenecks
            bottlenecks = await self._identify_bottlenecks(performance_analysis)
            
            return {
                "status": "success",
                "namespace": namespace,
                "egressip_count": len(egressips),
                "pod_assignments": len(pod_assignments),
                "performance_analysis": performance_analysis,
                "bottlenecks": bottlenecks,
                "recommendations": await self._generate_recommendations(bottlenecks),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing EgressIP performance: {e}")
            return {
                "status": "error",
                "error": str(e),
                "namespace": namespace,
                "timestamp": datetime.utcnow().isoformat()
            }

    # Helper methods for core functionality
    
    async def _execute_go_test(self, test_file: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Go test with specified configuration"""
        try:
            # Prepare test environment
            env = os.environ.copy()
            if self.kubeconfig_path:
                env['KUBECONFIG'] = self.kubeconfig_path
            
            # Create test wrapper script
            wrapper_script = self._create_go_test_wrapper(test_file, config)
            
            # Execute test
            start_time = time.time()
            process = await asyncio.create_subprocess_exec(
                'bash', wrapper_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            stdout, stderr = await process.communicate()
            execution_time = time.time() - start_time
            
            # Parse test results
            results = self._parse_go_test_output(stdout.decode(), stderr.decode())
            
            return {
                "execution_time": execution_time,
                "exit_code": process.returncode,
                "results": results,
                "stdout": stdout.decode(),
                "stderr": stderr.decode()
            }
            
        except Exception as e:
            logger.error(f"Error executing Go test: {e}")
            raise
    
    def _create_go_test_wrapper(self, test_file: str, config: Dict[str, Any]) -> str:
        """Create bash wrapper script for Go test execution"""
        wrapper_content = f"""#!/bin/bash
set -e

# Set test configuration
export EIP_OBJECT_COUNT={config.get('eip_object_count', 10)}
export PODS_PER_EIP={config.get('pods_per_eip', 200)}
export ITERATIONS={config.get('iterations', 20)}
export IP_STACK={config.get('ip_stack', 'auto')}
export PLATFORM={config.get('platform', 'auto')}

# Navigate to test directory
cd /home/sninganu/egress

# Run the specific test
ginkgo -v --focus="CORENET-6498" ./bk2openshift-tests-private/test/extended/networking/

echo "Test execution completed"
"""
        
        wrapper_path = self.test_results_dir / "go_test_wrapper.sh"
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_content)
        
        # Make executable
        os.chmod(wrapper_path, 0o755)
        
        return str(wrapper_path)
    
    def _parse_go_test_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """Parse Go test output and extract meaningful results"""
        results = {
            "test_passed": False,
            "scenarios_completed": 0,
            "total_scenarios": 4,
            "snat_rules_validated": False,
            "lrp_rules_validated": False,
            "pod_count_achieved": 0,
            "egressip_count_created": 0,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Parse stdout for test results
            if "Test completed successfully" in stdout:
                results["test_passed"] = True
            
            # Count completed scenarios
            for i in range(1, 5):
                if f"Scenario {i}" in stdout and "passed" in stdout:
                    results["scenarios_completed"] += 1
            
            # Extract pod and EgressIP counts
            import re
            pod_match = re.search(r'(\d+) total.*pods', stdout)
            if pod_match:
                results["pod_count_achieved"] = int(pod_match.group(1))
            
            eip_match = re.search(r'(\d+).*EgressIP.*objects', stdout)
            if eip_match:
                results["egressip_count_created"] = int(eip_match.group(1))
            
            # Check for rule validations
            if "SNAT rules verification passed" in stdout:
                results["snat_rules_validated"] = True
            if "LRP rules" in stdout and "verification passed" in stdout:
                results["lrp_rules_validated"] = True
            
            # Extract errors and warnings
            for line in stderr.split('\n'):
                if 'ERROR' in line.upper():
                    results["errors"].append(line.strip())
                elif 'WARN' in line.upper():
                    results["warnings"].append(line.strip())
                    
        except Exception as e:
            logger.warning(f"Error parsing test output: {e}")
        
        return results
    
    async def _get_ovn_snat_rules(self, node_name: str) -> List[str]:
        """Get SNAT rules from OVN on specific node"""
        try:
            cmd = [
                'oc', 'debug', f'node/{node_name}', '--',
                'chroot', '/host',
                'ovn-nbctl', '--no-leader-only',
                'lr-nat-list', 'ovn_cluster_router'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                rules = []
                for line in stdout.decode().split('\n'):
                    if 'snat' in line.lower():
                        rules.append(line.strip())
                return rules
            else:
                logger.error(f"Error getting SNAT rules: {stderr.decode()}")
                return []
                
        except Exception as e:
            logger.error(f"Error executing SNAT rules command: {e}")
            return []
    
    async def _get_ovn_lrp_rules(self, node_name: str) -> List[str]:
        """Get LRP rules from OVN on specific node"""
        try:
            cmd = [
                'oc', 'debug', f'node/{node_name}', '--',
                'chroot', '/host',
                'ovn-nbctl', '--no-leader-only',
                'lr-policy-list', 'ovn_cluster_router'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return [line.strip() for line in stdout.decode().split('\n') if line.strip()]
            else:
                logger.error(f"Error getting LRP rules: {stderr.decode()}")
                return []
                
        except Exception as e:
            logger.error(f"Error executing LRP rules command: {e}")
            return []
    
    async def _get_egressip_assignments(self) -> List[Dict[str, Any]]:
        """Get current EgressIP assignments"""
        try:
            cmd = ['oc', 'get', 'egressips', '-o', 'json']
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                data = json.loads(stdout.decode())
                assignments = []
                
                for item in data.get('items', []):
                    assignment = {
                        'name': item['metadata']['name'],
                        'egressIPs': item.get('spec', {}).get('egressIPs', []),
                        'status': item.get('status', {}),
                        'assignments': item.get('status', {}).get('items', [])
                    }
                    assignments.append(assignment)
                
                return assignments
            else:
                logger.error(f"Error getting EgressIP assignments: {stderr.decode()}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting EgressIP assignments: {e}")
            return []

# MCP Tool Definitions

@mcp.tool()
async def run_corenet_6498_test(
    eip_object_count: int = 10,
    pods_per_eip: int = 200,
    iterations: int = 20,
    ip_stack: str = "auto",
    platform: str = "auto"
) -> str:
    """
    Execute CORNET-6498 large-scale EgressIP stress test.
    
    This test creates multiple EgressIP objects with large numbers of pods and validates
    SNAT/LRP rules consistency under various stress conditions including node reboots,
    OVN pod restarts, and scaling operations.
    
    Args:
        eip_object_count: Number of EgressIP objects to create (default: 10)
        pods_per_eip: Number of pods per EgressIP object (default: 200)
        iterations: Number of test iterations per scenario (default: 20)
        ip_stack: IP stack type - auto, ipv4, ipv6, or dualstack (default: auto)
        platform: Target platform - auto, aws, gcp, azure, etc. (default: auto)
    
    Returns:
        JSON string containing test results, execution time, and analysis
    """
    analyzer = EgressIPAnalyzer()
    config = {
        "eip_object_count": eip_object_count,
        "pods_per_eip": pods_per_eip,
        "iterations": iterations,
        "ip_stack": ip_stack,
        "platform": platform
    }
    
    result = await analyzer.run_cornet_6498_test(config)
    return json.dumps(result, indent=2)


@mcp.tool()
async def validate_snat_lrp_rules(node_name: str) -> str:
    """
    Validate SNAT/LRP rules consistency on a specific OpenShift node.
    
    This tool examines the OVN database on the specified node to validate that
    SNAT and LRP (Logical Router Policy) rules are properly configured and
    consistent with the current EgressIP assignments.
    
    Args:
        node_name: Name of the OpenShift node to analyze
    
    Returns:
        JSON string containing rule counts, validation results, and any inconsistencies found
    """
    analyzer = EgressIPAnalyzer()
    result = await analyzer.validate_snat_lrp_rules(node_name)
    return json.dumps(result, indent=2)


@mcp.tool()
async def analyze_egressip_performance(namespace: str = None) -> str:
    """
    Analyze EgressIP performance metrics and identify potential bottlenecks.
    
    This tool examines EgressIP objects, pod assignments, traffic patterns,
    and node resource utilization to identify performance issues and provide
    optimization recommendations.
    
    Args:
        namespace: Specific namespace to analyze (optional, analyzes all if not specified)
    
    Returns:
        JSON string containing performance analysis, bottleneck identification, and recommendations
    """
    analyzer = EgressIPAnalyzer()
    result = await analyzer.analyze_egressip_performance(namespace)
    return json.dumps(result, indent=2)


@mcp.tool()
async def get_egressip_status() -> str:
    """
    Get comprehensive status of all EgressIP objects in the cluster.
    
    Returns detailed information about EgressIP objects including their current
    assignments, node distribution, and overall health status.
    
    Returns:
        JSON string containing EgressIP status information
    """
    try:
        analyzer = EgressIPAnalyzer()
        
        # Get EgressIP assignments
        assignments = await analyzer._get_egressip_assignments()
        
        # Get cluster nodes with egress labels
        cmd = ['oc', 'get', 'nodes', '-l', 'k8s.ovn.org/egress-assignable=true', '-o', 'json']
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        egress_nodes = []
        
        if process.returncode == 0:
            data = json.loads(stdout.decode())
            egress_nodes = [item['metadata']['name'] for item in data.get('items', [])]
        
        result = {
            "status": "success",
            "egressip_count": len(assignments),
            "egress_nodes_count": len(egress_nodes),
            "egress_nodes": egress_nodes,
            "egressip_objects": assignments,
            "summary": {
                "total_egressips_configured": sum(len(a.get('egressIPs', [])) for a in assignments),
                "total_assignments": sum(len(a.get('assignments', [])) for a in assignments),
                "nodes_with_assignments": len(set(
                    assignment.get('node', '') 
                    for a in assignments 
                    for assignment in a.get('assignments', [])
                    if assignment.get('node')
                ))
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error getting EgressIP status: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, indent=2)


@mcp.tool()
async def monitor_ovn_rules(node_name: str, duration_minutes: int = 5) -> str:
    """
    Monitor SNAT/LRP rule changes on a specific node over time.
    
    This tool continuously monitors OVN rule changes on the specified node
    to detect rule inconsistencies, missing rules, or unexpected changes.
    
    Args:
        node_name: Name of the OpenShift node to monitor
        duration_minutes: How long to monitor in minutes (default: 5)
    
    Returns:
        JSON string containing monitoring results and detected changes
    """
    try:
        analyzer = EgressIPAnalyzer()
        monitoring_results = []
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        logger.info(f"Starting OVN rules monitoring on {node_name} for {duration_minutes} minutes")
        
        while datetime.utcnow() < end_time:
            timestamp = datetime.utcnow()
            
            # Get current rules
            snat_rules = await analyzer._get_ovn_snat_rules(node_name)
            lrp_rules = await analyzer._get_ovn_lrp_rules(node_name)
            
            snapshot = {
                "timestamp": timestamp.isoformat(),
                "snat_rules_count": len(snat_rules),
                "lrp_rules_count": len(lrp_rules),
                "snat_rules_sample": snat_rules[:5],  # Sample for change detection
                "lrp_rules_sample": lrp_rules[:5]
            }
            
            monitoring_results.append(snapshot)
            
            # Sleep for 30 seconds between checks
            await asyncio.sleep(30)
        
        # Analyze changes
        changes_detected = []
        if len(monitoring_results) > 1:
            for i in range(1, len(monitoring_results)):
                prev = monitoring_results[i-1]
                curr = monitoring_results[i]
                
                if prev['snat_rules_count'] != curr['snat_rules_count']:
                    changes_detected.append({
                        "timestamp": curr['timestamp'],
                        "type": "snat_count_change",
                        "previous": prev['snat_rules_count'],
                        "current": curr['snat_rules_count']
                    })
                
                if prev['lrp_rules_count'] != curr['lrp_rules_count']:
                    changes_detected.append({
                        "timestamp": curr['timestamp'],
                        "type": "lrp_count_change",
                        "previous": prev['lrp_rules_count'],
                        "current": curr['lrp_rules_count']
                    })
        
        result = {
            "status": "success",
            "node_name": node_name,
            "monitoring_duration_minutes": duration_minutes,
            "snapshots_collected": len(monitoring_results),
            "changes_detected": changes_detected,
            "monitoring_data": monitoring_results,
            "summary": {
                "stable_monitoring": len(changes_detected) == 0,
                "total_changes": len(changes_detected)
            }
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        logger.error(f"Error monitoring OVN rules: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e),
            "node_name": node_name,
            "duration_minutes": duration_minutes
        }, indent=2)


if __name__ == "__main__":
    # Start the MCP server
    mcp.run(transport="stdio")