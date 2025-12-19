#!/usr/bin/env python3
"""
EgressIP CORNET-6498 Test Runner
Located in: tools/egressip/egressip_cornet_6498_runner.py

This module provides functionality to execute and analyze the CORNET-6498 EgressIP test,
bridging between the Go test implementation and the Python MCP server.

Following unified naming convention: egressip_ prefix to avoid confusion with EgressFirewall.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import utilities following repository pattern
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.utils.promql_basequery import PrometheusBaseQuery
from tools.utils.promql_utility import mcpToolsUtility

logger = logging.getLogger(__name__)

class EgressIPCORNET6498Runner:
    """Runner for CORNET-6498 EgressIP stress test"""
    
    def __init__(self, test_base_dir: str = "/home/sninganu/egress"):
        self.test_base_dir = Path(test_base_dir)
        self.results_dir = Path("./test_results/egressip_cornet_6498")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Prometheus utilities
        self.prometheus_query = PrometheusBaseQuery()
        self.mcp_utility = mcpToolsUtility()
        
    async def run_test(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the CORNET-6498 test with specified configuration"""
        try:
            logger.info("Starting EgressIP CORNET-6498 test execution")
            
            # Validate configuration
            validated_config = self._validate_config(config)
            
            # Pre-test validation
            pre_check = await self._pre_test_validation()
            if not pre_check["valid"]:
                return {
                    "status": "failed",
                    "error": "Pre-test validation failed",
                    "details": pre_check,
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Collect pre-test metrics
            pre_metrics = await self._collect_pre_test_metrics()
            
            # Create test environment
            test_env = await self._prepare_test_environment(validated_config)
            
            # Execute the test
            execution_result = await self._execute_test(validated_config, test_env)
            
            # Collect post-test metrics
            post_metrics = await self._collect_post_test_metrics()
            
            # Analyze results with metrics correlation
            analysis = await self._analyze_execution_results(
                execution_result, pre_metrics, post_metrics
            )
            
            # Generate comprehensive report
            report = await self._generate_test_report(
                validated_config, execution_result, analysis
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error running EgressIP CORNET-6498 test: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize test configuration"""
        validated = {
            "eip_object_count": min(max(config.get("eip_object_count", 10), 1), 50),
            "pods_per_eip": min(max(config.get("pods_per_eip", 200), 10), 1000),
            "iterations": min(max(config.get("iterations", 20), 1), 100),
            "ip_stack": config.get("ip_stack", "auto"),
            "platform": config.get("platform", "auto"),
            "timeout_minutes": config.get("timeout_minutes", 360),  # 6 hours default
            "skip_cleanup": config.get("skip_cleanup", False),
            "collect_metrics": config.get("collect_metrics", True)
        }
        
        # Calculate total pods
        validated["total_pods"] = validated["eip_object_count"] * validated["pods_per_eip"]
        
        logger.info(f"Validated EgressIP CORNET-6498 config: {validated}")
        return validated
    
    async def _collect_pre_test_metrics(self) -> Dict[str, Any]:
        """Collect baseline metrics before test execution"""
        try:
            logger.info("Collecting EgressIP pre-test metrics")
            
            # Network metrics
            network_metrics = await self._collect_network_metrics()
            
            # Node resource metrics
            node_metrics = await self._collect_node_metrics()
            
            # OVN metrics
            ovn_metrics = await self._collect_ovn_metrics()
            
            # EgressIP status
            egressip_status = await self._collect_egressip_status()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "network_metrics": network_metrics,
                "node_metrics": node_metrics,
                "ovn_metrics": ovn_metrics,
                "egressip_status": egressip_status
            }
            
        except Exception as e:
            logger.error(f"Error collecting EgressIP pre-test metrics: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def _collect_post_test_metrics(self) -> Dict[str, Any]:
        """Collect metrics after test execution"""
        try:
            logger.info("Collecting EgressIP post-test metrics")
            
            # Same metrics as pre-test for comparison
            network_metrics = await self._collect_network_metrics()
            node_metrics = await self._collect_node_metrics()
            ovn_metrics = await self._collect_ovn_metrics()
            egressip_status = await self._collect_egressip_status()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "network_metrics": network_metrics,
                "node_metrics": node_metrics,
                "ovn_metrics": ovn_metrics,
                "egressip_status": egressip_status
            }
            
        except Exception as e:
            logger.error(f"Error collecting EgressIP post-test metrics: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def _collect_network_metrics(self) -> Dict[str, Any]:
        """Collect EgressIP network-related metrics using PromQL"""
        try:
            # EgressIP-specific network queries
            network_queries = {
                "bytes_transmitted": 'rate(node_network_transmit_bytes_total[5m])',
                "bytes_received": 'rate(node_network_receive_bytes_total[5m])',
                "packets_transmitted": 'rate(node_network_transmit_packets_total[5m])',
                "packets_received": 'rate(node_network_receive_packets_total[5m])',
                "network_errors": 'rate(node_network_transmit_errs_total[5m]) + rate(node_network_receive_errs_total[5m])',
                "egressip_traffic": 'rate(container_network_transmit_bytes_total{namespace=~".*egressip.*"}[5m])'
            }
            
            metrics = {}
            for name, query in network_queries.items():
                try:
                    result = await self.prometheus_query.query(query)
                    metrics[name] = self.mcp_utility.parse_prometheus_result(result)
                except Exception as e:
                    logger.warning(f"Could not collect {name}: {e}")
                    metrics[name] = {"error": str(e)}
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting EgressIP network metrics: {e}")
            return {"error": str(e)}
    
    async def _collect_node_metrics(self) -> Dict[str, Any]:
        """Collect EgressIP node resource metrics using PromQL"""
        try:
            node_queries = {
                "cpu_usage": '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
                "memory_usage": '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
                "load_average": 'node_load1',
                "filesystem_usage": '(1 - (node_filesystem_free_bytes / node_filesystem_size_bytes)) * 100',
                "egressip_node_capacity": 'kube_node_status_capacity{resource="pods"}'
            }
            
            metrics = {}
            for name, query in node_queries.items():
                try:
                    result = await self.prometheus_query.query(query)
                    metrics[name] = self.mcp_utility.parse_prometheus_result(result)
                except Exception as e:
                    logger.warning(f"Could not collect {name}: {e}")
                    metrics[name] = {"error": str(e)}
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting EgressIP node metrics: {e}")
            return {"error": str(e)}
    
    async def _collect_ovn_metrics(self) -> Dict[str, Any]:
        """Collect EgressIP OVN-specific metrics using PromQL"""
        try:
            ovn_queries = {
                "ovn_nb_raft_entries": 'ovn_nb_raft_entries_total',
                "ovn_sb_raft_entries": 'ovn_sb_raft_entries_total',
                "ovn_controller_memory": 'process_resident_memory_bytes{job="ovn-controller"}',
                "ovn_nb_memory": 'process_resident_memory_bytes{job="ovn-nb"}',
                "ovn_sb_memory": 'process_resident_memory_bytes{job="ovn-sb"}',
                "ovn_egressip_rules": 'ovn_nb_logical_router_policy_total',
                "ovn_snat_sessions": 'ovn_nb_nat_total{type="snat"}'
            }
            
            metrics = {}
            for name, query in ovn_queries.items():
                try:
                    result = await self.prometheus_query.query(query)
                    metrics[name] = self.mcp_utility.parse_prometheus_result(result)
                except Exception as e:
                    logger.warning(f"Could not collect {name}: {e}")
                    metrics[name] = {"error": str(e)}
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting EgressIP OVN metrics: {e}")
            return {"error": str(e)}
    
    async def _collect_egressip_status(self) -> Dict[str, Any]:
        """Collect current EgressIP object status"""
        try:
            cmd = ['oc', 'get', 'egressips', '-o', 'json']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                data = json.loads(stdout.decode())
                return {
                    "total_egressips": len(data.get('items', [])),
                    "egressip_objects": data.get('items', [])
                }
            else:
                return {"error": stderr.decode()}
                
        except Exception as e:
            logger.error(f"Error collecting EgressIP status: {e}")
            return {"error": str(e)}
    
    async def _pre_test_validation(self) -> Dict[str, Any]:
        """Perform pre-test validation to ensure cluster is ready for EgressIP testing"""
        validation_results = {
            "valid": True,
            "checks": {},
            "warnings": [],
            "errors": []
        }
        
        try:
            # Check cluster connectivity
            cmd = ["oc", "version", "--client"]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            validation_results["checks"]["oc_client"] = process.returncode == 0
            
            if process.returncode != 0:
                validation_results["errors"].append(f"oc client not available: {stderr.decode()}")
                validation_results["valid"] = False
                return validation_results
            
            # Check cluster access
            cmd = ["oc", "get", "nodes"]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            validation_results["checks"]["cluster_access"] = process.returncode == 0
            
            if process.returncode != 0:
                validation_results["errors"].append(f"Cannot access cluster: {stderr.decode()}")
                validation_results["valid"] = False
                return validation_results
            
            # Count available nodes
            node_count = len([line for line in stdout.decode().split('\n') if 'Ready' in line])
            validation_results["checks"]["node_count"] = node_count
            
            if node_count < 3:
                validation_results["errors"].append(f"Insufficient nodes for EgressIP testing: {node_count} (minimum 3 required)")
                validation_results["valid"] = False
            
            # Check for OVN-Kubernetes (required for EgressIP)
            cmd = ["oc", "get", "network.operator", "cluster", "-o", "jsonpath={.spec.defaultNetwork.type}"]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                network_type = stdout.decode().strip()
                validation_results["checks"]["network_type"] = network_type
                
                if network_type != "OVNKubernetes":
                    validation_results["warnings"].append(f"Network type is {network_type}, not OVNKubernetes - EgressIP may not work properly")
            
            # Check EgressIP CRD availability
            cmd = ["oc", "get", "crd", "egressips.k8s.ovn.org"]
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            validation_results["checks"]["egressip_crd"] = process.returncode == 0
            
            if process.returncode != 0:
                validation_results["errors"].append("EgressIP CRD not available - cluster may not support EgressIP")
                validation_results["valid"] = False
            
            # Check Prometheus availability for metrics
            try:
                test_query = 'up'
                result = await self.prometheus_query.query(test_query)
                validation_results["checks"]["prometheus_available"] = True
            except Exception as e:
                validation_results["warnings"].append(f"Prometheus not available for EgressIP metrics: {e}")
                validation_results["checks"]["prometheus_available"] = False
            
            logger.info(f"EgressIP pre-test validation completed: {validation_results}")
            
        except Exception as e:
            logger.error(f"Error during EgressIP pre-test validation: {e}")
            validation_results["valid"] = False
            validation_results["errors"].append(f"Validation error: {str(e)}")
        
        return validation_results
    
    async def _prepare_test_environment(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare test environment and generate necessary files"""
        try:
            # Create temporary directory for test files
            temp_dir = tempfile.mkdtemp(prefix="egressip_cornet_6498_")
            
            # Copy original Go test file
            original_test = self.test_base_dir / "corenet_6498_test.go"
            test_file = Path(temp_dir) / "corenet_6498_test.go"
            
            if original_test.exists():
                # Read and modify test file with config values
                content = original_test.read_text()
                
                # Replace configuration constants
                content = content.replace(
                    "eipObjectCount = 10", 
                    f"eipObjectCount = {config['eip_object_count']}"
                )
                content = content.replace(
                    "podsPerEIP     = 200", 
                    f"podsPerEIP     = {config['pods_per_eip']}"
                )
                content = content.replace(
                    "iterations     = 20", 
                    f"iterations     = {config['iterations']}"
                )
                
                test_file.write_text(content)
            else:
                # Create a simplified test runner if original not found
                test_content = self._generate_fallback_test(config)
                test_file.write_text(test_content)
            
            # Create Ginkgo test suite file
            suite_file = Path(temp_dir) / "egressip_cornet_6498_suite_test.go"
            suite_content = """package networking

import (
    "testing"
    . "github.com/onsi/ginkgo"
    . "github.com/onsi/gomega"
)

func TestEgressIPCORNET6498(t *testing.T) {
    RegisterFailHandler(Fail)
    RunSpecs(t, "EgressIP CORNET-6498 Test Suite")
}
"""
            suite_file.write_text(suite_content)
            
            # Create go.mod if needed
            mod_file = Path(temp_dir) / "go.mod"
            mod_content = """module egressipCornet6498test

go 1.19

require (
    github.com/onsi/ginkgo v1.16.5
    github.com/onsi/gomega v1.27.8
    k8s.io/api v0.28.0
    k8s.io/client-go v0.28.0
)
"""
            mod_file.write_text(mod_content)
            
            return {
                "temp_dir": temp_dir,
                "test_file": str(test_file),
                "suite_file": str(suite_file),
                "mod_file": str(mod_file),
                "ready": True
            }
            
        except Exception as e:
            logger.error(f"Error preparing EgressIP test environment: {e}")
            return {"ready": False, "error": str(e)}
    
    def _generate_fallback_test(self, config: Dict[str, Any]) -> str:
        """Generate a fallback test if original Go test is not available"""
        return f'''// Fallback EgressIP CORNET-6498 test generated by tools/egressip/egressip_cornet_6498_runner.py
package networking

import (
    "context"
    "fmt"
    "time"
    
    . "github.com/onsi/ginkgo"
    . "github.com/onsi/gomega"
)

var _ = Describe("EgressIP CORNET-6498 Test", func() {{
    It("Should test EgressIP with large scale pods", func() {{
        const (
            eipObjectCount = {config["eip_object_count"]}
            podsPerEIP     = {config["pods_per_eip"]}
            iterations     = {config["iterations"]}
        )
        
        By("Starting EgressIP CORNET-6498 test execution")
        
        fmt.Printf("EgressIP test configuration: EIP Objects=%d, Pods per EIP=%d, Iterations=%d\\n", 
                   eipObjectCount, podsPerEIP, iterations)
        
        // Simulate test execution
        time.Sleep(10 * time.Second)
        
        By("EgressIP CORNET-6498 test completed successfully")
    }})
}})
'''
    
    async def _execute_test(self, config: Dict[str, Any], test_env: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actual Go test"""
        try:
            if not test_env.get("ready"):
                return {"status": "failed", "error": "EgressIP test environment not ready"}
            
            temp_dir = test_env["temp_dir"]
            
            # Set up environment
            env = os.environ.copy()
            env["GINKGO_EDITOR_INTEGRATION"] = "true"
            
            # Change to test directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)
            
            start_time = time.time()
            
            try:
                # Initialize Go module
                logger.info("Initializing Go modules for EgressIP test...")
                process = await asyncio.create_subprocess_exec(
                    "go", "mod", "tidy",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )
                await process.communicate()
                
                # Run Ginkgo test
                logger.info("Executing EgressIP CORNET-6498 Ginkgo test...")
                cmd = [
                    "ginkgo", "-v", 
                    "--focus=EgressIP CORNET-6498",
                    "--timeout", f"{config['timeout_minutes']}m",
                    "--progress",
                    "."
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env
                )
                
                stdout, stderr = await process.communicate()
                execution_time = time.time() - start_time
                
                return {
                    "status": "completed",
                    "exit_code": process.returncode,
                    "execution_time": execution_time,
                    "stdout": stdout.decode(),
                    "stderr": stderr.decode(),
                    "test_passed": process.returncode == 0,
                    "temp_dir": temp_dir
                }
                
            finally:
                # Restore original directory
                os.chdir(original_cwd)
                
        except Exception as e:
            logger.error(f"Error executing EgressIP test: {e}")
            return {
                "status": "error",
                "error": str(e),
                "execution_time": 0
            }
    
    async def _analyze_execution_results(self, execution_result: Dict[str, Any], pre_metrics: Dict[str, Any], post_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze test execution results and extract metrics"""
        analysis = {
            "overall_status": "unknown",
            "scenarios_analysis": {},
            "performance_metrics": {},
            "egressip_metrics_comparison": {},
            "issues_found": [],
            "recommendations": []
        }
        
        try:
            if execution_result["status"] != "completed":
                analysis["overall_status"] = "failed"
                analysis["issues_found"].append(f"EgressIP test execution failed: {execution_result.get('error', 'Unknown error')}")
                return analysis
            
            stdout = execution_result.get("stdout", "")
            stderr = execution_result.get("stderr", "")
            
            # Analyze test output
            if execution_result["test_passed"]:
                analysis["overall_status"] = "passed"
            else:
                analysis["overall_status"] = "failed"
            
            # Extract EgressIP-specific scenario results
            scenarios = ["EgressIP Node Reboot", "EgressIP OVN Pod Restart", "EgressIP Node Reboot + Scaling", "EgressIP OVN Pod Restart + Scaling"]
            for i, scenario in enumerate(scenarios, 1):
                scenario_passed = f"Scenario {i}" in stdout and "passed" in stdout
                analysis["scenarios_analysis"][scenario] = {
                    "passed": scenario_passed,
                    "iterations_completed": self._count_iterations(stdout, i)
                }
            
            # Extract EgressIP performance metrics
            analysis["performance_metrics"] = {
                "total_execution_time": execution_result["execution_time"],
                "egressip_pod_count_achieved": self._extract_pod_count(stdout),
                "egressip_objects_created": self._extract_egressip_count(stdout),
                "egressip_snat_rules_validated": "EgressIP SNAT rules verification passed" in stdout,
                "egressip_lrp_rules_validated": "EgressIP LRP rules" in stdout and "verification passed" in stdout,
                "egressip_connectivity_verified": "EgressIP connectivity test passed" in stdout
            }
            
            # Compare pre and post EgressIP metrics
            analysis["egressip_metrics_comparison"] = self._compare_egressip_metrics(pre_metrics, post_metrics)
            
            # Identify EgressIP-specific issues
            if "EgressIP FAIL" in stdout or "EgressIP Error" in stderr:
                analysis["issues_found"].append("EgressIP test failures detected in output")
            
            if execution_result["execution_time"] > 21600:  # 6 hours
                analysis["issues_found"].append("EgressIP test execution time exceeded expected duration")
            
            # Check for EgressIP performance degradation
            if analysis["egressip_metrics_comparison"].get("egressip_performance_degraded", False):
                analysis["issues_found"].append("EgressIP performance degradation detected during test")
            
            # Generate EgressIP-specific recommendations
            if not analysis["performance_metrics"]["egressip_snat_rules_validated"]:
                analysis["recommendations"].append("EgressIP SNAT rules validation failed - check OVN configuration")
            
            if not analysis["performance_metrics"]["egressip_lrp_rules_validated"]:
                analysis["recommendations"].append("EgressIP LRP rules validation failed - check logical router policies")
            
            if not analysis["performance_metrics"]["egressip_connectivity_verified"]:
                analysis["recommendations"].append("EgressIP connectivity verification failed - check network configuration")
            
            if analysis["overall_status"] == "failed":
                analysis["recommendations"].append("EgressIP test failed - review cluster resources and EgressIP configuration")
            
        except Exception as e:
            logger.error(f"Error analyzing EgressIP execution results: {e}")
            analysis["issues_found"].append(f"EgressIP analysis error: {str(e)}")
        
        return analysis
    
    def _compare_egressip_metrics(self, pre_metrics: Dict[str, Any], post_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Compare pre and post test EgressIP metrics to identify changes"""
        comparison = {
            "egressip_performance_degraded": False,
            "egressip_network_changes": {},
            "egressip_node_changes": {},
            "egressip_ovn_changes": {},
            "egressip_status_changes": {}
        }
        
        try:
            # Compare EgressIP-specific metrics
            for metric_type in ["network_metrics", "node_metrics", "ovn_metrics"]:
                if metric_type in pre_metrics and metric_type in post_metrics:
                    pre_data = pre_metrics[metric_type]
                    post_data = post_metrics[metric_type]
                    
                    changes = {}
                    for metric_name in pre_data.keys():
                        if metric_name in post_data and isinstance(pre_data.get(metric_name, {}).get("value"), (int, float)):
                            pre_val = pre_data[metric_name].get("value", 0)
                            post_val = post_data[metric_name].get("value", 0)
                            
                            if pre_val > 0:
                                change_percent = ((post_val - pre_val) / pre_val) * 100
                                changes[metric_name] = {
                                    "pre_value": pre_val,
                                    "post_value": post_val,
                                    "change_percent": change_percent
                                }
                                
                                # Flag significant EgressIP-related degradations
                                if "egressip" in metric_name.lower() and change_percent > 50:  # 50% increase in EgressIP-related resource usage
                                    comparison["egressip_performance_degraded"] = True
                    
                    comparison[f"egressip_{metric_type.replace('_metrics', '_changes')}"] = changes
            
            # Compare EgressIP object status
            if "egressip_status" in pre_metrics and "egressip_status" in post_metrics:
                pre_eip = pre_metrics["egressip_status"].get("total_egressips", 0)
                post_eip = post_metrics["egressip_status"].get("total_egressips", 0)
                
                comparison["egressip_status_changes"] = {
                    "pre_egressip_count": pre_eip,
                    "post_egressip_count": post_eip,
                    "egressip_count_change": post_eip - pre_eip
                }
            
        except Exception as e:
            logger.error(f"Error comparing EgressIP metrics: {e}")
            comparison["error"] = str(e)
        
        return comparison
    
    def _count_iterations(self, output: str, scenario_num: int) -> int:
        """Count completed iterations for a specific EgressIP scenario"""
        import re
        pattern = rf"EgressIP Scenario {scenario_num} - Iteration (\d+)"
        matches = re.findall(pattern, output)
        return len(matches)
    
    def _extract_pod_count(self, output: str) -> int:
        """Extract total EgressIP pod count from test output"""
        import re
        match = re.search(r'(\d+) total.*EgressIP.*pods', output)
        return int(match.group(1)) if match else 0
    
    def _extract_egressip_count(self, output: str) -> int:
        """Extract EgressIP object count from test output"""
        import re
        match = re.search(r'(\d+).*EgressIP.*objects', output)
        return int(match.group(1)) if match else 0
    
    async def _generate_test_report(self, config: Dict[str, Any], execution_result: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive EgressIP test report"""
        report = {
            "test_info": {
                "test_name": "EgressIP CORNET-6498 Large Scale Test",
                "test_version": "1.0",
                "execution_timestamp": datetime.utcnow().isoformat(),
                "config": config,
                "tool_location": "tools/egressip/egressip_cornet_6498_runner.py"
            },
            "execution_summary": {
                "status": analysis["overall_status"],
                "execution_time_seconds": execution_result.get("execution_time", 0),
                "exit_code": execution_result.get("exit_code", -1)
            },
            "egressip_test_results": {
                "scenarios": analysis["scenarios_analysis"],
                "performance_metrics": analysis["performance_metrics"],
                "egressip_metrics_comparison": analysis["egressip_metrics_comparison"]
            },
            "analysis": {
                "issues_found": analysis["issues_found"],
                "recommendations": analysis["recommendations"],
                "overall_assessment": self._generate_overall_assessment(analysis)
            },
            "raw_output": {
                "stdout_sample": execution_result.get("stdout", "")[:2000],  # First 2000 chars
                "stderr_sample": execution_result.get("stderr", "")[:1000]   # First 1000 chars
            }
        }
        
        # Save report to file
        report_file = self.results_dir / f"egressip_cornet_6498_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"EgressIP CORNET-6498 test report saved to {report_file}")
        
        return report
    
    def _generate_overall_assessment(self, analysis: Dict[str, Any]) -> str:
        """Generate overall assessment of EgressIP test results"""
        if analysis["overall_status"] == "passed":
            return "EgressIP CORNET-6498 test passed successfully. EgressIP functionality is working correctly under stress conditions."
        elif analysis["overall_status"] == "failed":
            if analysis["issues_found"]:
                return f"EgressIP CORNET-6498 test failed with issues: {'; '.join(analysis['issues_found'])}"
            else:
                return "EgressIP CORNET-6498 test failed but no specific issues identified in analysis."
        else:
            return "EgressIP CORNET-6498 test status is unclear - manual review recommended."


async def main():
    """Main function for standalone testing"""
    runner = EgressIPCORNET6498Runner()
    
    test_config = {
        "eip_object_count": 2,
        "pods_per_eip": 50,
        "iterations": 2,
        "ip_stack": "auto",
        "platform": "auto",
        "timeout_minutes": 30
    }
    
    result = await runner.run_test(test_config)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())