#!/usr/bin/env python3
"""
EgressIP OVN Rule Analyzer

This module provides comprehensive analysis of OVN SNAT and LRP rules,
specifically focused on EgressIP functionality and rule consistency validation.

Renamed with egressip_ prefix as per reviewer feedback.
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class EgressIPOVNRuleAnalyzer:
    """Analyzer for OVN SNAT and LRP rules related to EgressIP functionality"""
    
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.rule_patterns = {
            'snat': re.compile(r'snat\s+(\S+)\s+(\S+)\s+(\S+)'),
            'dnat': re.compile(r'dnat\s+(\S+)\s+(\S+)\s+(\S+)'),
            'lrp': re.compile(r'(\d+)\s+(\S+)\s+(\d+)\s+(.+)'),
            'egressip': re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
        }
        
        # Initialize Prometheus utilities for correlation - lazy import to avoid issues
        try:
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from tools.utils.promql_basequery import PrometheusBaseQuery
            from tools.utils.promql_utility import mcpToolsUtility
            self.prometheus_query = PrometheusBaseQuery(prometheus_url)
            self.mcp_utility = mcpToolsUtility()
        except ImportError as e:
            logger.warning(f"Could not initialize Prometheus utilities: {e}")
            self.prometheus_query = None
            self.mcp_utility = None
    
    async def analyze_node_rules(self, node_name: str) -> Dict[str, Any]:
        """Comprehensive analysis of OVN rules on a specific node"""
        try:
            logger.info(f"Starting EgressIP OVN rule analysis for node: {node_name}")
            
            # Get all rule types
            snat_rules = await self._get_egressip_snat_rules(node_name)
            lrp_rules = await self._get_egressip_lrp_rules(node_name)
            ovn_info = await self._get_egressip_ovn_database_info(node_name)
            
            # Analyze rules
            snat_analysis = await self._analyze_egressip_snat_rules(snat_rules)
            lrp_analysis = await self._analyze_egressip_lrp_rules(lrp_rules)
            consistency_check = await self._check_egressip_rule_consistency(snat_rules, lrp_rules)
            
            # Get EgressIP context
            egressip_context = await self._get_egressip_context()
            
            # Validate against current EgressIP assignments
            validation_results = await self._validate_rules_against_egressips(
                snat_rules, lrp_rules, egressip_context
            )
            
            return {
                "status": "success",
                "node_name": node_name,
                "timestamp": datetime.utcnow().isoformat(),
                "rule_counts": {
                    "snat_rules": len(snat_rules),
                    "lrp_rules": len(lrp_rules)
                },
                "snat_analysis": snat_analysis,
                "lrp_analysis": lrp_analysis,
                "consistency_check": consistency_check,
                "egressip_validation": validation_results,
                "ovn_database_info": ovn_info,
                "recommendations": await self._generate_egressip_recommendations(
                    snat_analysis, lrp_analysis, consistency_check, validation_results
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing EgressIP node rules: {e}")
            return {
                "status": "error",
                "error": str(e),
                "node_name": node_name,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def compare_egressip_rules_across_nodes(self, node_names: List[str]) -> Dict[str, Any]:
        """Compare EgressIP OVN rules across multiple nodes to identify inconsistencies"""
        try:
            logger.info(f"Comparing EgressIP rules across nodes: {node_names}")
            
            node_analyses = {}
            for node_name in node_names:
                node_analyses[node_name] = await self.analyze_node_rules(node_name)
            
            # Compare rule counts
            rule_count_comparison = self._compare_egressip_rule_counts(node_analyses)
            
            # Compare rule content
            rule_content_comparison = self._compare_egressip_rule_content(node_analyses)
            
            # Identify inconsistencies
            inconsistencies = self._identify_egressip_inconsistencies(rule_count_comparison, rule_content_comparison)
            
            return {
                "status": "success",
                "nodes_analyzed": node_names,
                "timestamp": datetime.utcnow().isoformat(),
                "rule_count_comparison": rule_count_comparison,
                "rule_content_comparison": rule_content_comparison,
                "inconsistencies": inconsistencies,
                "overall_consistency": len(inconsistencies) == 0,
                "recommendations": self._generate_multi_node_egressip_recommendations(inconsistencies)
            }
            
        except Exception as e:
            logger.error(f"Error comparing EgressIP rules across nodes: {e}")
            return {
                "status": "error",
                "error": str(e),
                "nodes_analyzed": node_names,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def monitor_egressip_rule_changes(self, node_name: str, duration_seconds: int = 300) -> Dict[str, Any]:
        """Monitor EgressIP rule changes over time to detect instability"""
        try:
            logger.info(f"Starting EgressIP rule monitoring on {node_name} for {duration_seconds}s")
            
            snapshots = []
            start_time = datetime.utcnow()
            
            # Take initial snapshot
            initial_snapshot = await self._take_egressip_rule_snapshot(node_name)
            snapshots.append(initial_snapshot)
            
            # Monitor for changes
            check_interval = min(30, duration_seconds // 10)  # At least 10 checks
            checks_remaining = duration_seconds // check_interval
            
            for i in range(checks_remaining):
                await asyncio.sleep(check_interval)
                snapshot = await self._take_egressip_rule_snapshot(node_name)
                snapshots.append(snapshot)
            
            # Analyze changes
            change_analysis = self._analyze_egressip_rule_changes(snapshots)
            
            return {
                "status": "success",
                "node_name": node_name,
                "monitoring_duration": duration_seconds,
                "snapshots_taken": len(snapshots),
                "timestamp": datetime.utcnow().isoformat(),
                "change_analysis": change_analysis,
                "stability_assessment": self._assess_egressip_rule_stability(change_analysis),
                "detailed_snapshots": snapshots
            }
            
        except Exception as e:
            logger.error(f"Error monitoring EgressIP rule changes: {e}")
            return {
                "status": "error",
                "error": str(e),
                "node_name": node_name,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _get_egressip_snat_rules(self, node_name: str) -> List[Dict[str, Any]]:
        """Get and parse EgressIP SNAT rules from OVN"""
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
            
            if process.returncode != 0:
                logger.error(f"Error getting EgressIP SNAT rules: {stderr.decode()}")
                return []
            
            rules = []
            for line in stdout.decode().split('\n'):
                line = line.strip()
                if 'snat' in line.lower():
                    parsed_rule = self._parse_egressip_snat_rule(line)
                    if parsed_rule:
                        rules.append(parsed_rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error executing EgressIP SNAT rules command: {e}")
            return []
    
    async def _get_egressip_lrp_rules(self, node_name: str) -> List[Dict[str, Any]]:
        """Get and parse EgressIP LRP rules from OVN"""
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
            
            if process.returncode != 0:
                logger.error(f"Error getting EgressIP LRP rules: {stderr.decode()}")
                return []
            
            rules = []
            for line in stdout.decode().split('\n'):
                line = line.strip()
                if line and not line.startswith('Routing'):
                    parsed_rule = self._parse_egressip_lrp_rule(line)
                    if parsed_rule:
                        rules.append(parsed_rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error executing EgressIP LRP rules command: {e}")
            return []
    
    def _parse_egressip_snat_rule(self, rule_line: str) -> Optional[Dict[str, Any]]:
        """Parse a single EgressIP SNAT rule line"""
        try:
            parts = rule_line.strip().split()
            if len(parts) >= 4 and parts[0].lower() == 'snat':
                return {
                    "type": "snat",
                    "external_ip": parts[1] if len(parts) > 1 else "",
                    "logical_ip": parts[2] if len(parts) > 2 else "",
                    "logical_port": parts[3] if len(parts) > 3 else "",
                    "raw_rule": rule_line,
                    "parsed_successfully": True,
                    "egressip_related": self._is_egressip_related_snat(rule_line)
                }
        except Exception as e:
            logger.warning(f"Failed to parse EgressIP SNAT rule: {rule_line}, error: {e}")
        
        return {
            "type": "snat",
            "raw_rule": rule_line,
            "parsed_successfully": False,
            "egressip_related": False
        }
    
    def _parse_egressip_lrp_rule(self, rule_line: str) -> Optional[Dict[str, Any]]:
        """Parse a single EgressIP LRP rule line"""
        try:
            # LRP format: priority match action
            parts = rule_line.strip().split(None, 2)
            if len(parts) >= 3:
                return {
                    "type": "lrp",
                    "priority": parts[0],
                    "match": parts[1],
                    "action": parts[2] if len(parts) > 2 else "",
                    "raw_rule": rule_line,
                    "parsed_successfully": True,
                    "egressip_related": self._is_egressip_related_lrp(rule_line)
                }
        except Exception as e:
            logger.warning(f"Failed to parse EgressIP LRP rule: {rule_line}, error: {e}")
        
        return {
            "type": "lrp",
            "raw_rule": rule_line,
            "parsed_successfully": False,
            "egressip_related": False
        }
    
    def _is_egressip_related_snat(self, rule_line: str) -> bool:
        """Determine if SNAT rule is related to EgressIP"""
        # Simple heuristic - look for EgressIP patterns
        return any([
            'egressip' in rule_line.lower(),
            'egress' in rule_line.lower() and 'ip' in rule_line.lower(),
            re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', rule_line)
        ])
    
    def _is_egressip_related_lrp(self, rule_line: str) -> bool:
        """Determine if LRP rule is related to EgressIP"""
        # Simple heuristic - look for EgressIP patterns
        return any([
            'egressip' in rule_line.lower(),
            'egress' in rule_line.lower() and 'ip' in rule_line.lower(),
            'reroute' in rule_line.lower(),
            re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', rule_line)
        ])
    
    async def _get_egressip_ovn_database_info(self, node_name: str) -> Dict[str, Any]:
        """Get EgressIP OVN database information"""
        try:
            cmd = [
                'oc', 'debug', f'node/{node_name}', '--',
                'chroot', '/host',
                'ovn-nbctl', '--no-leader-only',
                'show'
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                output = stdout.decode()
                return {
                    "available": True,
                    "output_sample": output[:1000],  # First 1000 chars
                    "line_count": len(output.split('\n')),
                    "contains_router_info": "ovn_cluster_router" in output.lower(),
                    "egressip_references": output.lower().count('egress')
                }
            else:
                return {
                    "available": False,
                    "error": stderr.decode()
                }
                
        except Exception as e:
            logger.error(f"Error getting EgressIP OVN database info: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    async def _get_egressip_context(self) -> Dict[str, Any]:
        """Get current EgressIP assignments for validation context"""
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
                
                egressips = []
                all_assigned_ips = set()
                
                for item in data.get('items', []):
                    egressip_info = {
                        'name': item['metadata']['name'],
                        'spec_ips': item.get('spec', {}).get('egressIPs', []),
                        'status_items': item.get('status', {}).get('items', [])
                    }
                    
                    # Collect all assigned IPs
                    for status_item in egressip_info['status_items']:
                        if 'egressIP' in status_item:
                            all_assigned_ips.add(status_item['egressIP'])
                    
                    egressips.append(egressip_info)
                
                return {
                    "available": True,
                    "egressip_objects": egressips,
                    "total_assigned_ips": list(all_assigned_ips),
                    "total_egressip_count": len(egressips)
                }
            else:
                return {
                    "available": False,
                    "error": stderr.decode()
                }
                
        except Exception as e:
            logger.error(f"Error getting EgressIP context: {e}")
            return {
                "available": False,
                "error": str(e)
            }
    
    async def _analyze_egressip_snat_rules(self, snat_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze EgressIP SNAT rules for patterns and issues"""
        analysis = {
            "total_rules": len(snat_rules),
            "parsed_successfully": sum(1 for rule in snat_rules if rule.get("parsed_successfully", False)),
            "egressip_related": sum(1 for rule in snat_rules if rule.get("egressip_related", False)),
            "external_ips": set(),
            "logical_ips": set(),
            "potential_issues": []
        }
        
        for rule in snat_rules:
            if rule.get("parsed_successfully", False):
                if rule.get("external_ip"):
                    analysis["external_ips"].add(rule["external_ip"])
                if rule.get("logical_ip"):
                    analysis["logical_ips"].add(rule["logical_ip"])
            else:
                analysis["potential_issues"].append(f"Failed to parse rule: {rule.get('raw_rule', '')}")
        
        # Convert sets to lists for JSON serialization
        analysis["external_ips"] = list(analysis["external_ips"])
        analysis["logical_ips"] = list(analysis["logical_ips"])
        analysis["unique_external_ips"] = len(analysis["external_ips"])
        analysis["unique_logical_ips"] = len(analysis["logical_ips"])
        
        return analysis
    
    async def _analyze_egressip_lrp_rules(self, lrp_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze EgressIP LRP rules for patterns and issues"""
        analysis = {
            "total_rules": len(lrp_rules),
            "parsed_successfully": sum(1 for rule in lrp_rules if rule.get("parsed_successfully", False)),
            "egressip_related": sum(1 for rule in lrp_rules if rule.get("egressip_related", False)),
            "priorities": [],
            "action_types": {},
            "potential_issues": []
        }
        
        for rule in lrp_rules:
            if rule.get("parsed_successfully", False):
                if rule.get("priority"):
                    try:
                        analysis["priorities"].append(int(rule["priority"]))
                    except ValueError:
                        analysis["potential_issues"].append(f"Invalid priority: {rule['priority']}")
                
                if rule.get("action"):
                    action = rule["action"].split()[0] if rule["action"] else "unknown"
                    analysis["action_types"][action] = analysis["action_types"].get(action, 0) + 1
            else:
                analysis["potential_issues"].append(f"Failed to parse rule: {rule.get('raw_rule', '')}")
        
        if analysis["priorities"]:
            analysis["priority_stats"] = {
                "min": min(analysis["priorities"]),
                "max": max(analysis["priorities"]),
                "unique_count": len(set(analysis["priorities"]))
            }
        else:
            analysis["priority_stats"] = {"min": 0, "max": 0, "unique_count": 0}
        
        return analysis
    
    async def _check_egressip_rule_consistency(self, snat_rules: List[Dict[str, Any]], lrp_rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check consistency between EgressIP SNAT and LRP rules"""
        consistency = {
            "snat_lrp_correlation": "unknown",
            "issues_found": [],
            "consistency_score": 0.0,
            "details": {}
        }
        
        try:
            # Extract external IPs from EgressIP SNAT rules
            snat_external_ips = set()
            for rule in snat_rules:
                if rule.get("parsed_successfully") and rule.get("external_ip") and rule.get("egressip_related"):
                    snat_external_ips.add(rule["external_ip"])
            
            # Look for corresponding LRP rules
            lrp_ip_references = set()
            for rule in lrp_rules:
                if rule.get("parsed_successfully") and rule.get("egressip_related"):
                    # Simple IP extraction from match and action fields
                    rule_text = f"{rule.get('match', '')} {rule.get('action', '')}"
                    ip_matches = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', rule_text)
                    lrp_ip_references.update(ip_matches)
            
            # Check correlation
            snat_in_lrp = snat_external_ips.intersection(lrp_ip_references)
            consistency["details"] = {
                "snat_external_ips": list(snat_external_ips),
                "lrp_ip_references": list(lrp_ip_references),
                "correlated_ips": list(snat_in_lrp)
            }
            
            if snat_external_ips and lrp_ip_references:
                consistency_ratio = len(snat_in_lrp) / len(snat_external_ips)
                consistency["consistency_score"] = consistency_ratio
                
                if consistency_ratio > 0.8:
                    consistency["snat_lrp_correlation"] = "good"
                elif consistency_ratio > 0.5:
                    consistency["snat_lrp_correlation"] = "moderate"
                else:
                    consistency["snat_lrp_correlation"] = "poor"
                    consistency["issues_found"].append("Low correlation between EgressIP SNAT and LRP rules")
            
        except Exception as e:
            logger.error(f"Error checking EgressIP rule consistency: {e}")
            consistency["issues_found"].append(f"Consistency check error: {str(e)}")
        
        return consistency
    
    async def _validate_rules_against_egressips(self, snat_rules: List[Dict[str, Any]], lrp_rules: List[Dict[str, Any]], egressip_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate OVN rules against current EgressIP assignments"""
        validation = {
            "validation_possible": egressip_context.get("available", False),
            "missing_snat_rules": [],
            "unexpected_snat_rules": [],
            "validation_summary": {}
        }
        
        if not validation["validation_possible"]:
            validation["error"] = egressip_context.get("error", "EgressIP context not available")
            return validation
        
        try:
            assigned_ips = set(egressip_context.get("total_assigned_ips", []))
            snat_external_ips = set()
            
            for rule in snat_rules:
                if rule.get("parsed_successfully") and rule.get("external_ip") and rule.get("egressip_related"):
                    snat_external_ips.add(rule["external_ip"])
            
            # Find missing and unexpected rules
            validation["missing_snat_rules"] = list(assigned_ips - snat_external_ips)
            validation["unexpected_snat_rules"] = list(snat_external_ips - assigned_ips)
            
            validation["validation_summary"] = {
                "total_assigned_egressips": len(assigned_ips),
                "total_snat_external_ips": len(snat_external_ips),
                "missing_rules_count": len(validation["missing_snat_rules"]),
                "unexpected_rules_count": len(validation["unexpected_snat_rules"]),
                "validation_passed": len(validation["missing_snat_rules"]) == 0 and len(validation["unexpected_snat_rules"]) == 0
            }
            
        except Exception as e:
            logger.error(f"Error validating EgressIP rules against assignments: {e}")
            validation["error"] = str(e)
        
        return validation
    
    async def _generate_egressip_recommendations(self, snat_analysis: Dict[str, Any], lrp_analysis: Dict[str, Any], consistency_check: Dict[str, Any], validation_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations based on EgressIP analysis results"""
        recommendations = []
        
        # EgressIP SNAT rule recommendations
        if snat_analysis["total_rules"] == 0:
            recommendations.append("No EgressIP SNAT rules found - check if EgressIP objects are properly configured")
        elif snat_analysis["parsed_successfully"] < snat_analysis["total_rules"]:
            recommendations.append("Some EgressIP SNAT rules failed to parse - review OVN rule format")
        elif snat_analysis["egressip_related"] == 0:
            recommendations.append("No EgressIP-related SNAT rules detected - verify EgressIP assignments")
        
        # EgressIP LRP rule recommendations
        if lrp_analysis["total_rules"] == 0:
            recommendations.append("No EgressIP LRP rules found - this may indicate OVN configuration issues")
        elif lrp_analysis["parsed_successfully"] < lrp_analysis["total_rules"]:
            recommendations.append("Some EgressIP LRP rules failed to parse - review OVN rule format")
        elif lrp_analysis["egressip_related"] == 0:
            recommendations.append("No EgressIP-related LRP rules detected - check logical router policies")
        
        # EgressIP consistency recommendations
        if consistency_check["consistency_score"] < 0.5:
            recommendations.append("Poor correlation between EgressIP SNAT and LRP rules - investigate OVN rule synchronization")
        
        # EgressIP validation recommendations
        if validation_results.get("validation_possible"):
            if validation_results["validation_summary"].get("missing_rules_count", 0) > 0:
                recommendations.append(f"Missing EgressIP SNAT rules for {validation_results['validation_summary']['missing_rules_count']} EgressIPs - check OVN rule creation")
            
            if validation_results["validation_summary"].get("unexpected_rules_count", 0) > 0:
                recommendations.append(f"Found {validation_results['validation_summary']['unexpected_rules_count']} unexpected EgressIP SNAT rules - check for stale rules")
        
        if not recommendations:
            recommendations.append("EgressIP OVN rules analysis shows no major issues - monitoring and periodic validation recommended")
        
        return recommendations
    
    async def _take_egressip_rule_snapshot(self, node_name: str) -> Dict[str, Any]:
        """Take a snapshot of current EgressIP rules for monitoring"""
        snat_rules = await self._get_egressip_snat_rules(node_name)
        lrp_rules = await self._get_egressip_lrp_rules(node_name)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "snat_count": len(snat_rules),
            "lrp_count": len(lrp_rules),
            "egressip_snat_count": sum(1 for r in snat_rules if r.get("egressip_related", False)),
            "egressip_lrp_count": sum(1 for r in lrp_rules if r.get("egressip_related", False)),
            "snat_rules_hash": hash(str(sorted([r.get("raw_rule", "") for r in snat_rules]))),
            "lrp_rules_hash": hash(str(sorted([r.get("raw_rule", "") for r in lrp_rules])))
        }
    
    def _analyze_egressip_rule_changes(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze changes across EgressIP rule snapshots"""
        if len(snapshots) < 2:
            return {"changes_detected": False, "reason": "Insufficient snapshots"}
        
        changes = []
        for i in range(1, len(snapshots)):
            prev = snapshots[i-1]
            curr = snapshots[i]
            
            snapshot_changes = {}
            
            if prev["snat_count"] != curr["snat_count"]:
                snapshot_changes["snat_count_change"] = {
                    "from": prev["snat_count"],
                    "to": curr["snat_count"],
                    "timestamp": curr["timestamp"]
                }
            
            if prev["lrp_count"] != curr["lrp_count"]:
                snapshot_changes["lrp_count_change"] = {
                    "from": prev["lrp_count"],
                    "to": curr["lrp_count"],
                    "timestamp": curr["timestamp"]
                }
            
            if prev["egressip_snat_count"] != curr["egressip_snat_count"]:
                snapshot_changes["egressip_snat_count_change"] = {
                    "from": prev["egressip_snat_count"],
                    "to": curr["egressip_snat_count"],
                    "timestamp": curr["timestamp"]
                }
            
            if prev["egressip_lrp_count"] != curr["egressip_lrp_count"]:
                snapshot_changes["egressip_lrp_count_change"] = {
                    "from": prev["egressip_lrp_count"],
                    "to": curr["egressip_lrp_count"],
                    "timestamp": curr["timestamp"]
                }
            
            if prev["snat_rules_hash"] != curr["snat_rules_hash"]:
                snapshot_changes["snat_content_change"] = {
                    "timestamp": curr["timestamp"]
                }
            
            if prev["lrp_rules_hash"] != curr["lrp_rules_hash"]:
                snapshot_changes["lrp_content_change"] = {
                    "timestamp": curr["timestamp"]
                }
            
            if snapshot_changes:
                changes.append(snapshot_changes)
        
        return {
            "changes_detected": len(changes) > 0,
            "total_change_events": len(changes),
            "changes": changes
        }
    
    def _assess_egressip_rule_stability(self, change_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the stability of EgressIP rules based on change analysis"""
        if not change_analysis["changes_detected"]:
            return {
                "stability": "stable",
                "assessment": "No EgressIP rule changes detected during monitoring period",
                "confidence": "high"
            }
        
        change_count = change_analysis["total_change_events"]
        
        if change_count <= 2:
            return {
                "stability": "mostly_stable",
                "assessment": f"Minor EgressIP changes detected ({change_count} events)",
                "confidence": "medium"
            }
        else:
            return {
                "stability": "unstable",
                "assessment": f"Frequent EgressIP rule changes detected ({change_count} events)",
                "confidence": "high"
            }

    def _compare_egressip_rule_counts(self, node_analyses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Compare rule counts across nodes"""
        comparison = {}
        for node_name, analysis in node_analyses.items():
            if analysis["status"] == "success":
                comparison[node_name] = analysis["rule_counts"]
        return comparison

    def _compare_egressip_rule_content(self, node_analyses: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Compare rule content across nodes"""
        comparison = {}
        for node_name, analysis in node_analyses.items():
            if analysis["status"] == "success":
                comparison[node_name] = {
                    "snat_external_ips": analysis["snat_analysis"].get("external_ips", []),
                    "lrp_priorities": analysis["lrp_analysis"].get("priorities", [])
                }
        return comparison

    def _identify_egressip_inconsistencies(self, rule_count_comparison: Dict[str, Any], rule_content_comparison: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify inconsistencies in EgressIP rules across nodes"""
        inconsistencies = []
        
        # Check for rule count inconsistencies
        if len(set(str(rc) for rc in rule_count_comparison.values())) > 1:
            inconsistencies.append({
                "type": "rule_count_mismatch",
                "description": "Different rule counts across nodes",
                "details": rule_count_comparison
            })
        
        # Check for content inconsistencies
        if len(rule_content_comparison) > 1:
            all_snat_ips = set()
            for node_data in rule_content_comparison.values():
                all_snat_ips.update(node_data.get("snat_external_ips", []))
            
            for node_name, node_data in rule_content_comparison.items():
                node_ips = set(node_data.get("snat_external_ips", []))
                missing_ips = all_snat_ips - node_ips
                if missing_ips:
                    inconsistencies.append({
                        "type": "missing_snat_ips",
                        "node": node_name,
                        "description": f"Missing SNAT IPs on node {node_name}",
                        "missing_ips": list(missing_ips)
                    })
        
        return inconsistencies

    def _generate_multi_node_egressip_recommendations(self, inconsistencies: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on multi-node inconsistencies"""
        recommendations = []
        
        for inconsistency in inconsistencies:
            if inconsistency["type"] == "rule_count_mismatch":
                recommendations.append("Rule count mismatch detected across nodes - verify EgressIP distribution")
            elif inconsistency["type"] == "missing_snat_ips":
                recommendations.append(f"Missing SNAT IPs on {inconsistency['node']} - check EgressIP assignment")
        
        if not inconsistencies:
            recommendations.append("EgressIP rules are consistent across all analyzed nodes")
        
        return recommendations


async def main():
    """Main function for standalone testing"""
    analyzer = EgressIPOVNRuleAnalyzer()
    
    # Example usage
    result = await analyzer.analyze_node_rules("worker-0")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())