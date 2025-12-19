#!/usr/bin/env python3
"""
EgressIP Metrics Collector
Located in: tools/egressip/egressip_metrics_collector.py

This module collects, processes, and stores EgressIP-related performance metrics
for long-term analysis and trend identification.

Following unified naming convention: egressip_ prefix to avoid confusion with EgressFirewall.
"""

import asyncio
import json
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess

# Import utilities following repository pattern
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.utils.promql_basequery import PrometheusBaseQuery
from tools.utils.promql_utility import mcpToolsUtility

logger = logging.getLogger(__name__)

class EgressIPMetricsCollector:
    """Collector for EgressIP performance and operational metrics"""
    
    def __init__(self, database_path: str = "./storage/egressip_metrics.db"):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize Prometheus utilities for EgressIP metrics
        self.prometheus_query = PrometheusBaseQuery()
        self.mcp_utility = mcpToolsUtility()
        
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for EgressIP metrics storage"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Create tables for different EgressIP metric types
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS egressip_status (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        egressip_name TEXT NOT NULL,
                        namespace TEXT,
                        status TEXT,
                        assigned_node TEXT,
                        assigned_ip TEXT,
                        pod_count INTEGER,
                        egressip_metrics_json TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS egressip_ovn_rule_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        node_name TEXT NOT NULL,
                        egressip_snat_rules_count INTEGER,
                        egressip_lrp_rules_count INTEGER,
                        egressip_parsing_errors INTEGER,
                        egressip_consistency_score REAL,
                        egressip_metrics_json TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS egressip_performance_tests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        egressip_test_name TEXT NOT NULL,
                        egressip_test_config_json TEXT,
                        egressip_execution_time_seconds REAL,
                        egressip_test_passed BOOLEAN,
                        egressip_scenarios_completed INTEGER,
                        egressip_total_scenarios INTEGER,
                        egressip_metrics_json TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS egressip_cluster_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        total_nodes INTEGER,
                        egressip_capable_nodes INTEGER,
                        total_egressips INTEGER,
                        total_pods_with_egressip INTEGER,
                        egressip_network_type TEXT,
                        egressip_prometheus_metrics_json TEXT,
                        egressip_metrics_json TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS egressip_network_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        node_name TEXT,
                        egressip_bytes_transmitted_rate REAL,
                        egressip_bytes_received_rate REAL,
                        egressip_packets_transmitted_rate REAL,
                        egressip_packets_received_rate REAL,
                        egressip_network_errors_rate REAL,
                        egressip_traffic_rate REAL,
                        egressip_metrics_json TEXT
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS egressip_trend_analysis (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        egressip_metric_type TEXT NOT NULL,
                        egressip_trend_direction TEXT,
                        egressip_confidence_score REAL,
                        egressip_data_points INTEGER,
                        egressip_analysis_period_days INTEGER,
                        egressip_trend_json TEXT
                    )
                """)
                
                # Create indices for better query performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_egressip_status_timestamp ON egressip_status(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_egressip_ovn_timestamp ON egressip_ovn_rule_metrics(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_egressip_perf_timestamp ON egressip_performance_tests(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_egressip_cluster_timestamp ON egressip_cluster_metrics(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_egressip_network_timestamp ON egressip_network_metrics(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_egressip_trend_timestamp ON egressip_trend_analysis(timestamp)")
                
                # Create indices on EgressIP-specific fields
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_egressip_name ON egressip_status(egressip_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_egressip_node ON egressip_ovn_rule_metrics(node_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_egressip_test_name ON egressip_performance_tests(egressip_test_name)")
                
                conn.commit()
                logger.info("EgressIP metrics database initialized successfully")
                
        except Exception as e:
            logger.error(f"Error initializing EgressIP metrics database: {e}")
            raise
    
    async def collect_egressip_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive EgressIP metrics"""
        try:
            logger.info("Collecting EgressIP metrics")
            
            # Get all EgressIP objects
            egressips = await self._get_egressip_objects()
            
            # Get EgressIP pod assignments
            egressip_pod_assignments = await self._get_egressip_pod_assignments()
            
            # Collect EgressIP-specific Prometheus metrics
            egressip_prometheus_metrics = await self._collect_egressip_prometheus_metrics()
            
            # Process each EgressIP object
            egressip_metrics = []
            for egressip in egressips:
                egressip_metric = await self._process_egressip_object(egressip, egressip_pod_assignments)
                egressip_metrics.append(egressip_metric)
            
            # Store EgressIP metrics in database
            timestamp = datetime.utcnow().isoformat()
            for metric in egressip_metrics:
                await self._store_egressip_metric(timestamp, metric)
            
            return {
                "status": "success",
                "timestamp": timestamp,
                "egressip_metrics_collected": len(egressip_metrics),
                "egressip_prometheus_metrics": egressip_prometheus_metrics,
                "egressip_metrics": egressip_metrics
            }
            
        except Exception as e:
            logger.error(f"Error collecting EgressIP metrics: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def collect_egressip_network_metrics(self) -> Dict[str, Any]:
        """Collect EgressIP network metrics"""
        try:
            logger.info("Collecting EgressIP network metrics")
            
            timestamp = datetime.utcnow().isoformat()
            
            # EgressIP-specific network queries
            egressip_network_queries = {
                "egressip_bytes_transmitted_rate": 'rate(node_network_transmit_bytes_total[5m])',
                "egressip_bytes_received_rate": 'rate(node_network_receive_bytes_total[5m])',
                "egressip_packets_transmitted_rate": 'rate(node_network_transmit_packets_total[5m])',
                "egressip_packets_received_rate": 'rate(node_network_receive_packets_total[5m])',
                "egressip_network_errors_rate": 'rate(node_network_transmit_errs_total[5m]) + rate(node_network_receive_errs_total[5m])',
                "egressip_traffic_rate": 'rate(container_network_transmit_bytes_total{namespace=~".*egressip.*"}[5m])',
                "egressip_ovn_nb_connections": 'ovn_nb_e2e_timestamp',
                "egressip_ovn_sb_connections": 'ovn_sb_e2e_timestamp'
            }
            
            egressip_metrics = {}
            for name, query in egressip_network_queries.items():
                try:
                    result = await self.prometheus_query.query(query)
                    parsed_result = self.mcp_utility.parse_prometheus_result(result)
                    egressip_metrics[name] = parsed_result
                except Exception as e:
                    logger.warning(f"Could not collect EgressIP metric {name}: {e}")
                    egressip_metrics[name] = {"error": str(e)}
            
            # Store EgressIP network metrics by node
            await self._store_egressip_network_metrics(timestamp, egressip_metrics)
            
            return {
                "status": "success",
                "timestamp": timestamp,
                "egressip_network_metrics": egressip_metrics
            }
            
        except Exception as e:
            logger.error(f"Error collecting EgressIP network metrics: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _collect_egressip_prometheus_metrics(self) -> Dict[str, Any]:
        """Collect EgressIP-specific Prometheus metrics"""
        try:
            egressip_prometheus_queries = {
                "egressip_service_external_ips": 'kube_service_spec_external_ips',
                "egressip_node_capacity": 'kube_node_status_capacity{resource="pods"}',
                "egressip_node_allocatable": 'kube_node_status_allocatable{resource="pods"}',
                "egressip_ovn_controller_memory": 'process_resident_memory_bytes{job="ovn-controller"}',
                "egressip_ovn_nb_raft_entries": 'ovn_nb_raft_entries_total',
                "egressip_ovn_sb_raft_entries": 'ovn_sb_raft_entries_total',
                "egressip_container_network_transmit": 'rate(container_network_transmit_bytes_total[5m])',
                "egressip_container_network_receive": 'rate(container_network_receive_bytes_total[5m])',
                "egressip_ovn_logical_router_policies": 'ovn_nb_logical_router_policy_total',
                "egressip_ovn_nat_rules": 'ovn_nb_nat_total{type="snat"}'
            }
            
            egressip_metrics = {}
            for name, query in egressip_prometheus_queries.items():
                try:
                    result = await self.prometheus_query.query(query)
                    egressip_metrics[name] = self.mcp_utility.parse_prometheus_result(result)
                except Exception as e:
                    logger.warning(f"Could not collect EgressIP Prometheus metric {name}: {e}")
                    egressip_metrics[name] = {"error": str(e)}
            
            return egressip_metrics
            
        except Exception as e:
            logger.error(f"Error collecting EgressIP Prometheus metrics: {e}")
            return {"error": str(e)}
    
    async def collect_egressip_ovn_rule_metrics(self, node_names: List[str]) -> Dict[str, Any]:
        """Collect EgressIP OVN rule metrics from specified nodes"""
        try:
            logger.info(f"Collecting EgressIP OVN rule metrics from {len(node_names)} nodes")
            
            egressip_ovn_metrics = []
            timestamp = datetime.utcnow().isoformat()
            
            for node_name in node_names:
                egressip_node_metric = await self._collect_egressip_node_ovn_metrics(node_name)
                egressip_node_metric["node_name"] = node_name
                egressip_node_metric["timestamp"] = timestamp
                egressip_ovn_metrics.append(egressip_node_metric)
                
                # Store in database
                await self._store_egressip_ovn_rule_metric(timestamp, egressip_node_metric)
            
            return {
                "status": "success",
                "timestamp": timestamp,
                "egressip_nodes_analyzed": len(node_names),
                "egressip_ovn_metrics": egressip_ovn_metrics
            }
            
        except Exception as e:
            logger.error(f"Error collecting EgressIP OVN rule metrics: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def collect_egressip_cluster_metrics(self) -> Dict[str, Any]:
        """Collect cluster-wide EgressIP metrics with Prometheus integration"""
        try:
            logger.info("Collecting cluster-wide EgressIP metrics")
            
            # Get EgressIP cluster information
            egressip_cluster_info = await self._get_egressip_cluster_info()
            
            # Get EgressIP network configuration
            egressip_network_info = await self._get_egressip_network_info()
            
            # Count EgressIP-related resources
            egressip_count = await self._count_egressip_objects()
            egressip_pod_count = await self._count_pods_with_egressip()
            
            # Collect EgressIP Prometheus metrics
            egressip_prometheus_metrics = await self._collect_egressip_prometheus_metrics()
            
            timestamp = datetime.utcnow().isoformat()
            egressip_cluster_metrics = {
                "timestamp": timestamp,
                "total_nodes": egressip_cluster_info.get("node_count", 0),
                "egressip_capable_nodes": egressip_cluster_info.get("egressip_capable_nodes", 0),
                "total_egressips": egressip_count,
                "total_pods_with_egressip": egressip_pod_count,
                "egressip_network_type": egressip_network_info.get("network_type", "unknown"),
                "egressip_cluster_info": egressip_cluster_info,
                "egressip_network_info": egressip_network_info,
                "egressip_prometheus_metrics": egressip_prometheus_metrics
            }
            
            # Store in database
            await self._store_egressip_cluster_metric(timestamp, egressip_cluster_metrics)
            
            return {
                "status": "success",
                "egressip_cluster_metrics": egressip_cluster_metrics
            }
            
        except Exception as e:
            logger.error(f"Error collecting EgressIP cluster metrics: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def store_egressip_performance_test_result(self, test_name: str, config: Dict[str, Any], results: Dict[str, Any]) -> bool:
        """Store EgressIP performance test results in database"""
        try:
            timestamp = datetime.utcnow().isoformat()
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO egressip_performance_tests 
                    (timestamp, egressip_test_name, egressip_test_config_json, egressip_execution_time_seconds, 
                     egressip_test_passed, egressip_scenarios_completed, egressip_total_scenarios, egressip_metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    f"egressip_{test_name}",
                    json.dumps(config),
                    results.get("execution_time", 0),
                    results.get("test_passed", False),
                    results.get("scenarios_completed", 0),
                    results.get("total_scenarios", 0),
                    json.dumps(results)
                ))
                conn.commit()
            
            logger.info(f"Stored EgressIP performance test result: {test_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing EgressIP performance test result: {e}")
            return False
    
    async def get_egressip_metrics_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get summary of EgressIP metrics from the last N hours"""
        try:
            cutoff_time = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # EgressIP status metrics summary
                cursor.execute("""
                    SELECT COUNT(*) as total_records,
                           COUNT(DISTINCT egressip_name) as unique_egressips,
                           AVG(pod_count) as avg_pod_count
                    FROM egressip_status 
                    WHERE timestamp > ?
                """, (cutoff_time,))
                egressip_status_summary = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
                
                # EgressIP OVN rule metrics summary
                cursor.execute("""
                    SELECT COUNT(*) as total_records,
                           COUNT(DISTINCT node_name) as unique_nodes,
                           AVG(egressip_snat_rules_count) as avg_egressip_snat_rules,
                           AVG(egressip_lrp_rules_count) as avg_egressip_lrp_rules,
                           AVG(egressip_consistency_score) as avg_egressip_consistency_score
                    FROM egressip_ovn_rule_metrics 
                    WHERE timestamp > ?
                """, (cutoff_time,))
                egressip_ovn_summary = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
                
                # EgressIP performance test summary
                cursor.execute("""
                    SELECT COUNT(*) as total_egressip_tests,
                           COUNT(CASE WHEN egressip_test_passed = 1 THEN 1 END) as passed_egressip_tests,
                           AVG(egressip_execution_time_seconds) as avg_egressip_execution_time
                    FROM egressip_performance_tests 
                    WHERE timestamp > ?
                """, (cutoff_time,))
                egressip_perf_summary = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
                
                # EgressIP network metrics summary
                cursor.execute("""
                    SELECT COUNT(*) as total_records,
                           AVG(egressip_bytes_transmitted_rate) as avg_egressip_transmit_rate,
                           AVG(egressip_bytes_received_rate) as avg_egressip_receive_rate,
                           AVG(egressip_network_errors_rate) as avg_egressip_error_rate
                    FROM egressip_network_metrics 
                    WHERE timestamp > ?
                """, (cutoff_time,))
                egressip_network_summary = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
                
                # Recent EgressIP cluster metrics
                cursor.execute("""
                    SELECT * FROM egressip_cluster_metrics 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (cutoff_time,))
                egressip_cluster_result = cursor.fetchone()
                egressip_cluster_summary = {}
                if egressip_cluster_result:
                    egressip_cluster_summary = dict(zip([col[0] for col in cursor.description], egressip_cluster_result))
                
                return {
                    "status": "success",
                    "egressip_time_range_hours": hours_back,
                    "egressip_cutoff_time": cutoff_time,
                    "egressip_status_metrics": egressip_status_summary,
                    "egressip_ovn_rule_metrics": egressip_ovn_summary,
                    "egressip_performance_tests": egressip_perf_summary,
                    "egressip_network_metrics": egressip_network_summary,
                    "latest_egressip_cluster_metrics": egressip_cluster_summary
                }
                
        except Exception as e:
            logger.error(f"Error getting EgressIP metrics summary: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_egressip_trend_analysis(self, metric_type: str, days_back: int = 7) -> Dict[str, Any]:
        """Analyze trends in EgressIP metrics over time"""
        try:
            cutoff_time = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                if metric_type == "egressip_status":
                    cursor.execute("""
                        SELECT DATE(timestamp) as date,
                               COUNT(DISTINCT egressip_name) as unique_egressips,
                               AVG(pod_count) as avg_egressip_pod_count,
                               COUNT(*) as total_records
                        FROM egressip_status 
                        WHERE timestamp > ?
                        GROUP BY DATE(timestamp)
                        ORDER BY date
                    """, (cutoff_time,))
                    
                elif metric_type == "egressip_network":
                    cursor.execute("""
                        SELECT DATE(timestamp) as date,
                               AVG(egressip_bytes_transmitted_rate) as avg_egressip_transmit_rate,
                               AVG(egressip_bytes_received_rate) as avg_egressip_receive_rate,
                               AVG(egressip_network_errors_rate) as avg_egressip_error_rate,
                               COUNT(*) as total_records
                        FROM egressip_network_metrics 
                        WHERE timestamp > ?
                        GROUP BY DATE(timestamp)
                        ORDER BY date
                    """, (cutoff_time,))
                    
                elif metric_type == "egressip_ovn_rules":
                    cursor.execute("""
                        SELECT DATE(timestamp) as date,
                               AVG(egressip_snat_rules_count) as avg_egressip_snat_rules,
                               AVG(egressip_lrp_rules_count) as avg_egressip_lrp_rules,
                               AVG(egressip_consistency_score) as avg_egressip_consistency,
                               COUNT(*) as total_records
                        FROM egressip_ovn_rule_metrics 
                        WHERE timestamp > ?
                        GROUP BY DATE(timestamp)
                        ORDER BY date
                    """, (cutoff_time,))
                    
                elif metric_type == "egressip_performance_tests":
                    cursor.execute("""
                        SELECT DATE(timestamp) as date,
                               COUNT(*) as total_egressip_tests,
                               COUNT(CASE WHEN egressip_test_passed = 1 THEN 1 END) as passed_egressip_tests,
                               AVG(egressip_execution_time_seconds) as avg_egressip_execution_time
                        FROM egressip_performance_tests 
                        WHERE timestamp > ?
                        GROUP BY DATE(timestamp)
                        ORDER BY date
                    """, (cutoff_time,))
                
                else:
                    return {
                        "status": "error",
                        "error": f"Unknown EgressIP metric type: {metric_type}"
                    }
                
                egressip_trend_results = cursor.fetchall()
                egressip_trend_columns = [col[0] for col in cursor.description]
                
                egressip_trend_data = []
                for row in egressip_trend_results:
                    egressip_trend_data.append(dict(zip(egressip_trend_columns, row)))
                
                # Calculate EgressIP trend indicators
                egressip_trend_analysis = self._calculate_egressip_trends(egressip_trend_data, metric_type)
                
                # Store trend analysis
                await self._store_egressip_trend_analysis(metric_type, egressip_trend_analysis, days_back)
                
                return {
                    "status": "success",
                    "egressip_metric_type": metric_type,
                    "egressip_days_analyzed": days_back,
                    "egressip_data_points": len(egressip_trend_data),
                    "egressip_trend_data": egressip_trend_data,
                    "egressip_trend_analysis": egressip_trend_analysis
                }
                
        except Exception as e:
            logger.error(f"Error analyzing EgressIP trends: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _store_egressip_trend_analysis(self, metric_type: str, trend_analysis: Dict[str, Any], days_back: int):
        """Store EgressIP trend analysis results"""
        try:
            timestamp = datetime.utcnow().isoformat()
            
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO egressip_trend_analysis 
                    (timestamp, egressip_metric_type, egressip_trend_direction, egressip_confidence_score,
                     egressip_data_points, egressip_analysis_period_days, egressip_trend_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    metric_type,
                    trend_analysis.get("overall_trend", "unknown"),
                    trend_analysis.get("confidence", 0.0),
                    trend_analysis.get("data_points", 0),
                    days_back,
                    json.dumps(trend_analysis)
                ))
                conn.commit()
            
        except Exception as e:
            logger.error(f"Error storing EgressIP trend analysis: {e}")
    
    def _calculate_egressip_trends(self, data: List[Dict[str, Any]], metric_type: str) -> Dict[str, Any]:
        """Calculate trend indicators from EgressIP time series data"""
        if len(data) < 2:
            return {"trend": "insufficient_data", "details": "Need at least 2 data points for EgressIP trend analysis"}
        
        try:
            if metric_type == "egressip_status":
                # Analyze EgressIP object trends
                egressip_counts = [d.get("unique_egressips", 0) for d in data]
                egressip_pod_counts = [d.get("avg_egressip_pod_count", 0) for d in data if d.get("avg_egressip_pod_count") is not None]
                
                return {
                    "egressip_object_trend": self._simple_trend(egressip_counts),
                    "egressip_pod_count_trend": self._simple_trend(egressip_pod_counts) if egressip_pod_counts else "no_data",
                    "egressip_latest_values": {
                        "unique_egressips": egressip_counts[-1] if egressip_counts else 0,
                        "avg_egressip_pod_count": egressip_pod_counts[-1] if egressip_pod_counts else 0
                    },
                    "overall_trend": self._simple_trend(egressip_counts),
                    "confidence": 0.8,
                    "data_points": len(data)
                }
                
            elif metric_type == "egressip_network":
                # Analyze EgressIP network performance trends
                egressip_transmit_rates = [d.get("avg_egressip_transmit_rate", 0) for d in data if d.get("avg_egressip_transmit_rate") is not None]
                egressip_receive_rates = [d.get("avg_egressip_receive_rate", 0) for d in data if d.get("avg_egressip_receive_rate") is not None]
                egressip_error_rates = [d.get("avg_egressip_error_rate", 0) for d in data if d.get("avg_egressip_error_rate") is not None]
                
                return {
                    "egressip_transmit_rate_trend": self._simple_trend(egressip_transmit_rates) if egressip_transmit_rates else "no_data",
                    "egressip_receive_rate_trend": self._simple_trend(egressip_receive_rates) if egressip_receive_rates else "no_data",
                    "egressip_error_rate_trend": self._simple_trend(egressip_error_rates) if egressip_error_rates else "no_data",
                    "overall_trend": self._simple_trend(egressip_transmit_rates) if egressip_transmit_rates else "no_data",
                    "confidence": 0.7,
                    "data_points": len(data)
                }
                
            elif metric_type == "egressip_ovn_rules":
                # Analyze EgressIP OVN rule trends
                egressip_snat_counts = [d.get("avg_egressip_snat_rules", 0) for d in data if d.get("avg_egressip_snat_rules") is not None]
                egressip_lrp_counts = [d.get("avg_egressip_lrp_rules", 0) for d in data if d.get("avg_egressip_lrp_rules") is not None]
                egressip_consistency_scores = [d.get("avg_egressip_consistency", 0) for d in data if d.get("avg_egressip_consistency") is not None]
                
                return {
                    "egressip_snat_rules_trend": self._simple_trend(egressip_snat_counts) if egressip_snat_counts else "no_data",
                    "egressip_lrp_rules_trend": self._simple_trend(egressip_lrp_counts) if egressip_lrp_counts else "no_data",
                    "egressip_consistency_trend": self._simple_trend(egressip_consistency_scores) if egressip_consistency_scores else "no_data",
                    "overall_trend": self._simple_trend(egressip_snat_counts) if egressip_snat_counts else "no_data",
                    "confidence": 0.9,
                    "data_points": len(data)
                }
                
            elif metric_type == "egressip_performance_tests":
                # Analyze EgressIP performance test trends
                egressip_execution_times = [d.get("avg_egressip_execution_time", 0) for d in data if d.get("avg_egressip_execution_time") is not None]
                egressip_pass_rates = []
                
                for d in data:
                    total = d.get("total_egressip_tests", 0)
                    passed = d.get("passed_egressip_tests", 0)
                    if total > 0:
                        egressip_pass_rates.append(passed / total)
                
                return {
                    "egressip_execution_time_trend": self._simple_trend(egressip_execution_times) if egressip_execution_times else "no_data",
                    "egressip_pass_rate_trend": self._simple_trend(egressip_pass_rates) if egressip_pass_rates else "no_data",
                    "overall_trend": self._simple_trend(egressip_pass_rates) if egressip_pass_rates else "no_data",
                    "confidence": 0.85,
                    "data_points": len(data)
                }
            
        except Exception as e:
            logger.error(f"Error calculating EgressIP trends: {e}")
            return {"trend": "calculation_error", "error": str(e)}
        
        return {"trend": "unknown"}
    
    def _simple_trend(self, values: List[float]) -> str:
        """Calculate simple trend direction from a list of values"""
        if len(values) < 2:
            return "insufficient_data"
        
        # Calculate average of first half vs second half
        mid_point = len(values) // 2
        first_half_avg = sum(values[:mid_point]) / mid_point if mid_point > 0 else 0
        second_half_avg = sum(values[mid_point:]) / (len(values) - mid_point)
        
        diff_percent = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        
        if diff_percent > 10:
            return "increasing"
        elif diff_percent < -10:
            return "decreasing"
        else:
            return "stable"
    
    # Helper methods for EgressIP data collection
    
    async def _get_egressip_objects(self) -> List[Dict[str, Any]]:
        """Get all EgressIP objects from cluster"""
        try:
            cmd = ['oc', 'get', 'egressips', '-o', 'json']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                data = json.loads(stdout.decode())
                return data.get('items', [])
            else:
                logger.error(f"Error getting EgressIP objects: {stderr.decode()}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting EgressIP objects: {e}")
            return []
    
    async def _get_egressip_pod_assignments(self) -> Dict[str, List[str]]:
        """Get pods assigned to each EgressIP"""
        # This would require more complex logic to map pods to EgressIPs
        # For now, return empty dict - would need full implementation
        return {}
    
    async def _process_egressip_object(self, egressip: Dict[str, Any], egressip_pod_assignments: Dict[str, List[str]]) -> Dict[str, Any]:
        """Process individual EgressIP object to extract metrics"""
        try:
            egressip_name = egressip['metadata']['name']
            egressip_namespace = egressip['metadata'].get('namespace', 'cluster-wide')
            
            egressip_spec = egressip.get('spec', {})
            egressip_status = egressip.get('status', {})
            
            # Extract key EgressIP metrics
            egressip_metrics = {
                "egressip_name": egressip_name,
                "egressip_namespace": egressip_namespace,
                "egressip_spec_ips": egressip_spec.get('egressIPs', []),
                "egressip_status_items": egressip_status.get('items', []),
                "egressip_pod_count": len(egressip_pod_assignments.get(egressip_name, [])),
                "egressip_assigned_nodes": list(set(item.get('node', '') for item in egressip_status.get('items', []) if item.get('node'))),
                "egressip_assigned_ips": list(set(item.get('egressIP', '') for item in egressip_status.get('items', []) if item.get('egressIP')))
            }
            
            # Determine overall EgressIP status
            if len(egressip_metrics["egressip_status_items"]) == len(egressip_metrics["egressip_spec_ips"]):
                egressip_metrics["egressip_status"] = "ready"
            elif len(egressip_metrics["egressip_status_items"]) > 0:
                egressip_metrics["egressip_status"] = "partial"
            else:
                egressip_metrics["egressip_status"] = "pending"
            
            return egressip_metrics
            
        except Exception as e:
            logger.error(f"Error processing EgressIP object: {e}")
            return {"egressip_name": "unknown", "error": str(e)}
    
    async def _store_egressip_metric(self, timestamp: str, egressip_metric: Dict[str, Any]):
        """Store EgressIP metric in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO egressip_status 
                    (timestamp, egressip_name, namespace, status, assigned_node, assigned_ip, pod_count, egressip_metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    egressip_metric.get("egressip_name", ""),
                    egressip_metric.get("egressip_namespace", ""),
                    egressip_metric.get("egressip_status", "unknown"),
                    ",".join(egressip_metric.get("egressip_assigned_nodes", [])),
                    ",".join(egressip_metric.get("egressip_assigned_ips", [])),
                    egressip_metric.get("egressip_pod_count", 0),
                    json.dumps(egressip_metric)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing EgressIP metric: {e}")

    async def _store_egressip_network_metrics(self, timestamp: str, egressip_metrics: Dict[str, Any]):
        """Store EgressIP network metrics in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO egressip_network_metrics 
                    (timestamp, node_name, egressip_bytes_transmitted_rate, egressip_bytes_received_rate, 
                     egressip_packets_transmitted_rate, egressip_packets_received_rate, egressip_network_errors_rate, 
                     egressip_traffic_rate, egressip_metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    "egressip-cluster-aggregate",  # Aggregate EgressIP metrics for now
                    self._extract_metric_value(egressip_metrics.get("egressip_bytes_transmitted_rate", {})),
                    self._extract_metric_value(egressip_metrics.get("egressip_bytes_received_rate", {})),
                    self._extract_metric_value(egressip_metrics.get("egressip_packets_transmitted_rate", {})),
                    self._extract_metric_value(egressip_metrics.get("egressip_packets_received_rate", {})),
                    self._extract_metric_value(egressip_metrics.get("egressip_network_errors_rate", {})),
                    self._extract_metric_value(egressip_metrics.get("egressip_traffic_rate", {})),
                    json.dumps(egressip_metrics)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing EgressIP network metrics: {e}")

    def _extract_metric_value(self, metric_data: Dict[str, Any]) -> float:
        """Extract numeric value from metric data"""
        try:
            if isinstance(metric_data, dict):
                if "value" in metric_data:
                    return float(metric_data["value"])
                elif "values" in metric_data and metric_data["values"]:
                    return float(metric_data["values"][-1])
            return 0.0
        except (ValueError, TypeError, KeyError):
            return 0.0

    async def _collect_egressip_node_ovn_metrics(self, node_name: str) -> Dict[str, Any]:
        """Collect EgressIP OVN metrics for a specific node"""
        # Import the EgressIP OVN analyzer
        try:
            from .egressip_ovn_rule_analyzer import EgressIPOVNRuleAnalyzer
        except ImportError:
            # Fallback if import fails
            logger.warning("Could not import EgressIP OVN rule analyzer, using mock data")
            return {
                "egressip_snat_rules_count": 0,
                "egressip_lrp_rules_count": 0,
                "egressip_parsing_errors": 0,
                "egressip_consistency_score": 0.0,
                "error": "EgressIP OVN analyzer not available"
            }
        
        egressip_ovn_analyzer = EgressIPOVNRuleAnalyzer()
        result = await egressip_ovn_analyzer.analyze_node_rules(node_name)
        
        if result["status"] == "success":
            return {
                "egressip_snat_rules_count": result["rule_counts"]["egressip_snat_rules"],
                "egressip_lrp_rules_count": result["rule_counts"]["egressip_lrp_rules"],
                "egressip_parsing_errors": len(result["snat_analysis"]["potential_issues"]) + len(result["lrp_analysis"]["potential_issues"]),
                "egressip_consistency_score": result["consistency_check"].get("consistency_score", 0.0)
            }
        else:
            return {
                "egressip_snat_rules_count": 0,
                "egressip_lrp_rules_count": 0,
                "egressip_parsing_errors": 1,
                "egressip_consistency_score": 0.0,
                "error": result.get("error", "Unknown EgressIP error")
            }

    async def _store_egressip_ovn_rule_metric(self, timestamp: str, egressip_metric: Dict[str, Any]):
        """Store EgressIP OVN rule metric in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO egressip_ovn_rule_metrics 
                    (timestamp, node_name, egressip_snat_rules_count, egressip_lrp_rules_count, 
                     egressip_parsing_errors, egressip_consistency_score, egressip_metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    egressip_metric.get("node_name", ""),
                    egressip_metric.get("egressip_snat_rules_count", 0),
                    egressip_metric.get("egressip_lrp_rules_count", 0),
                    egressip_metric.get("egressip_parsing_errors", 0),
                    egressip_metric.get("egressip_consistency_score", 0.0),
                    json.dumps(egressip_metric)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing EgressIP OVN rule metric: {e}")

    async def _get_egressip_cluster_info(self) -> Dict[str, Any]:
        """Get basic EgressIP cluster information"""
        try:
            # Get total node count
            cmd = ['oc', 'get', 'nodes', '--no-headers']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            node_count = len(stdout.decode().strip().split('\n')) if stdout else 0
            
            # Get EgressIP-capable nodes
            cmd = ['oc', 'get', 'nodes', '-l', 'k8s.ovn.org/egress-assignable=true', '--no-headers']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            egressip_capable_nodes = len(stdout.decode().strip().split('\n')) if stdout and stdout.strip() else 0
            
            return {
                "node_count": node_count,
                "egressip_capable_nodes": egressip_capable_nodes
            }
            
        except Exception as e:
            logger.error(f"Error getting EgressIP cluster info: {e}")
            return {"node_count": 0, "egressip_capable_nodes": 0}

    async def _get_egressip_network_info(self) -> Dict[str, Any]:
        """Get EgressIP cluster network configuration"""
        try:
            cmd = ['oc', 'get', 'network.operator', 'cluster', '-o', 'json']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                data = json.loads(stdout.decode())
                egressip_network_type = data.get('spec', {}).get('defaultNetwork', {}).get('type', 'unknown')
                return {"network_type": egressip_network_type}
            
        except Exception as e:
            logger.error(f"Error getting EgressIP network info: {e}")
        
        return {"network_type": "unknown"}

    async def _count_egressip_objects(self) -> int:
        """Count total EgressIP objects"""
        try:
            cmd = ['oc', 'get', 'egressips', '--no-headers']
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            return len(stdout.decode().strip().split('\n')) if stdout and stdout.strip() else 0
            
        except Exception as e:
            logger.error(f"Error counting EgressIP objects: {e}")
            return 0

    async def _count_pods_with_egressip(self) -> int:
        """Count pods that have EgressIP assignments"""
        # This would require complex label/namespace matching
        # For now, return 0 - would need full implementation for EgressIP pod counting
        return 0

    async def _store_egressip_cluster_metric(self, timestamp: str, egressip_metrics: Dict[str, Any]):
        """Store EgressIP cluster metric in database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO egressip_cluster_metrics 
                    (timestamp, total_nodes, egressip_capable_nodes, total_egressips, 
                     total_pods_with_egressip, egressip_network_type, egressip_prometheus_metrics_json, egressip_metrics_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    timestamp,
                    egressip_metrics.get("total_nodes", 0),
                    egressip_metrics.get("egressip_capable_nodes", 0),
                    egressip_metrics.get("total_egressips", 0),
                    egressip_metrics.get("total_pods_with_egressip", 0),
                    egressip_metrics.get("egressip_network_type", "unknown"),
                    json.dumps(egressip_metrics.get("egressip_prometheus_metrics", {})),
                    json.dumps(egressip_metrics)
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Error storing EgressIP cluster metric: {e}")


async def main():
    """Main function for standalone testing"""
    egressip_collector = EgressIPMetricsCollector()
    
    # Test EgressIP metrics collection
    result = await egressip_collector.collect_egressip_cluster_metrics()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())