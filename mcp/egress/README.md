# EgressIP Performance Analyzer MCP Server

A comprehensive AI-powered performance analysis and testing platform for OpenShift EgressIP functionality, built on the Model Context Protocol (MCP) framework.

## Overview

The EgressIP Performance Analyzer provides advanced testing, monitoring, and analysis capabilities for OpenShift EgressIP implementations. It integrates large-scale performance testing (like CORENET-6498) with continuous monitoring and AI-powered bottleneck detection.

## Features

### 🚀 **Large-Scale Performance Testing**
- **CORENET-6498 Integration**: Execute large-scale EgressIP stress tests with 2000+ pods
- **Multi-Scenario Testing**: Node reboots, OVN pod restarts, scaling operations
- **IPv4/IPv6 Support**: Comprehensive dual-stack testing capabilities
- **Automated Validation**: SNAT/LRP rule consistency verification

### 🔍 **Advanced OVN Analysis**
- **Rule Validation**: Comprehensive SNAT and LRP rule analysis
- **Consistency Checking**: Cross-node rule consistency validation
- **Real-time Monitoring**: Continuous rule change detection
- **Performance Correlation**: Link OVN rules to performance metrics

### 📊 **Metrics Collection & Analysis**
- **Time-Series Storage**: Long-term metrics storage with SQLite backend
- **Trend Analysis**: Automated trend detection and forecasting
- **Performance Tracking**: EgressIP and cluster-wide performance metrics
- **Custom Dashboards**: Integration-ready metrics export

### 🤖 **AI-Powered Insights**
- **Natural Language Queries**: Ask questions about EgressIP performance
- **Automated Recommendations**: AI-generated optimization suggestions
- **Bottleneck Detection**: Intelligent performance issue identification
- **Predictive Analysis**: Trend-based performance predictions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Agent Layer                          │
│  (LangGraph-powered agents for intelligent analysis)        │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                  MCP Server Layer                           │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐  │
│  │  Test Runner    │ │  OVN Analyzer   │ │ Metrics       │  │
│  │  Tools          │ │  Tools          │ │ Collector     │  │
│  └─────────────────┘ └─────────────────┘ └───────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                 Tools/Collectors Layer                      │
│  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐  │
│  │ CORENET-6498    │ │ OVN Rule        │ │ Performance   │  │
│  │ Test Runner     │ │ Analyzer        │ │ Metrics DB    │  │
│  └─────────────────┘ └─────────────────┘ └───────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────────┐
│                Infrastructure Layer                         │
│        OpenShift/Kubernetes Cluster + OVN-Kubernetes       │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- OpenShift cluster with OVN-Kubernetes networking
- Python 3.8+
- Go 1.19+ (for test execution)
- Ginkgo test framework
- `oc` CLI tool configured

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ocp-performance-analyzer-mcp/mcp/egress
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the server**:
   ```bash
   cp config/egress_config.yaml config/local_config.yaml
   # Edit local_config.yaml as needed
   ```

4. **Initialize the database**:
   ```bash
   python tools/metrics_collector.py
   ```

### Running the MCP Server

```bash
# Start the server
python egress_analyzer_mcp_server.py

# The server will listen on stdio for MCP protocol messages
```

### Using with AI Agents

The server provides MCP tools that can be used by AI agents (Claude, etc.) for natural language interaction:

```python
# Example: Ask AI agent to run a performance test
"Run a CORENET-6498 test with 5 EgressIP objects and 100 pods each"

# Example: Analyze current cluster state
"Check the SNAT/LRP rule consistency on worker-0"

# Example: Get performance insights
"What are the current EgressIP performance trends?"
```

## Available MCP Tools

### 🔧 **Testing Tools**

#### `run_cornet_6498_test`
Execute the CORENET-6498 large-scale EgressIP stress test.

**Parameters:**
- `eip_object_count` (int): Number of EgressIP objects (default: 10)
- `pods_per_eip` (int): Pods per EgressIP object (default: 200)
- `iterations` (int): Test iterations per scenario (default: 20)
- `ip_stack` (str): IP stack type - auto/ipv4/ipv6/dualstack
- `platform` (str): Platform type - auto/aws/gcp/azure/etc.

**Example:**
```json
{
  "eip_object_count": 5,
  "pods_per_eip": 100,
  "iterations": 10,
  "ip_stack": "ipv4",
  "platform": "aws"
}
```

### 🔍 **Analysis Tools**

#### `validate_snat_lrp_rules`
Validate SNAT/LRP rules consistency on a specific node.

**Parameters:**
- `node_name` (str): OpenShift node name to analyze

#### `analyze_egressip_performance`
Analyze EgressIP performance metrics and identify bottlenecks.

**Parameters:**
- `namespace` (str, optional): Specific namespace to analyze

#### `get_egressip_status`
Get comprehensive status of all EgressIP objects in the cluster.

#### `monitor_ovn_rules`
Monitor SNAT/LRP rule changes over time on a specific node.

**Parameters:**
- `node_name` (str): Node name to monitor
- `duration_minutes` (int): Monitoring duration (default: 5)

## Configuration

The server behavior can be customized through `config/egress_config.yaml`:

### Test Configuration
```yaml
test_config:
  cornet_6498:
    default_eip_objects: 10
    default_pods_per_eip: 200
    default_iterations: 20
    default_timeout_minutes: 360
```

### Performance Thresholds
```yaml
performance_thresholds:
  rule_validation:
    max_snat_rules_per_node: 10000
    rule_consistency_min_score: 0.8
```

### Metrics Collection
```yaml
metrics:
  collection_schedule:
    egressip_metrics_interval_minutes: 15
    ovn_rules_interval_minutes: 30
```

## Test Scenarios

### CORENET-6498 Test Scenarios

1. **Node Reboot Scenario**
   - Setup: Multiple EgressIP objects with large pod counts
   - Action: Reboot EgressIP nodes
   - Validation: SNAT/LRP rule consistency

2. **OVN Pod Restart Scenario**
   - Setup: Large-scale pod deployments
   - Action: Kill and restart OVN pods
   - Validation: Rule recreation and consistency

3. **Concurrent Operations Scenario**
   - Setup: Active EgressIP configurations
   - Action: Node operations + pod scaling
   - Validation: Rule stability under load

4. **Stress Testing Scenario**
   - Setup: Maximum supported scale
   - Action: Combined stress operations
   - Validation: System limits and recovery

## Metrics and Analysis

### Collected Metrics

- **EgressIP Status**: Object state, assignments, pod counts
- **OVN Rules**: SNAT/LRP rule counts, consistency scores
- **Performance Tests**: Execution times, pass rates, scenarios
- **Cluster Metrics**: Node counts, resource utilization

### Trend Analysis

The system automatically analyzes trends in:
- EgressIP object growth over time
- Rule consistency scores
- Test performance metrics
- Cluster resource usage

### Performance Insights

AI-powered analysis provides:
- Bottleneck identification
- Optimization recommendations
- Predictive scaling advice
- Root cause analysis

## Integration Examples

### With Prometheus/Grafana
```bash
# Export metrics for Prometheus scraping
curl -s http://localhost:8080/metrics | grep egressip
```

### With CI/CD Pipelines
```yaml
# Example Jenkins pipeline step
steps:
  - name: "EgressIP Performance Test"
    script: |
      python -c "
      import asyncio
      from egress_analyzer import run_cornet_6498_test
      result = asyncio.run(run_cornet_6498_test(
        eip_object_count=3,
        pods_per_eip=50,
        iterations=5
      ))
      exit(0 if result['status'] == 'success' else 1)
      "
```

### With AI Assistants
```python
# Natural language queries via MCP protocol
"How many SNAT rules are currently configured on worker-1?"
"Run a small-scale EgressIP test to verify the cluster is healthy"
"Show me the EgressIP performance trends from the last week"
```

## Troubleshooting

### Common Issues

1. **Test Execution Failures**
   ```bash
   # Check cluster prerequisites
   python tools/validate_cluster.py
   
   # Verify Go test environment
   cd /home/sninganu/egress && go mod tidy
   ```

2. **OVN Rule Analysis Issues**
   ```bash
   # Test OVN connectivity
   oc debug node/worker-0 -- chroot /host ovn-nbctl show
   
   # Check node accessibility
   oc get nodes -l k8s.ovn.org/egress-assignable=true
   ```

3. **Metrics Collection Problems**
   ```bash
   # Verify database initialization
   python -c "from tools.metrics_collector import EgressIPMetricsCollector; EgressIPMetricsCollector()"
   
   # Check cluster permissions
   oc auth can-i get egressips --all-namespaces
   ```

### Debug Mode

Enable debug logging:
```yaml
# In config/egress_config.yaml
development:
  debug_mode: true
  verbose_logging: true
```

## Performance Recommendations

### Optimal Test Configuration

For **production clusters**:
```yaml
test_config:
  eip_object_count: 5-10
  pods_per_eip: 50-100
  iterations: 10-20
```

For **development clusters**:
```yaml
test_config:
  eip_object_count: 2-5
  pods_per_eip: 20-50
  iterations: 5-10
```

### Resource Requirements

- **Minimum**: 3 worker nodes, 16GB RAM, 8 CPU cores
- **Recommended**: 6+ worker nodes, 64GB+ RAM, 24+ CPU cores
- **Large Scale**: 10+ worker nodes, 128GB+ RAM, 48+ CPU cores

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add comprehensive tests
4. Update documentation
5. Submit a pull request

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Code formatting
black .
isort .
```

## License

Apache-2.0 - See [LICENSE](LICENSE) file for details.

## Support

For issues and support:
- Create GitHub issues for bugs and feature requests
- Join OpenShift performance scale team discussions
- Review existing documentation and examples

## Related Projects

- [OpenShift OVN-Kubernetes](https://github.com/ovn-org/ovn-kubernetes)
- [OpenShift Performance Scale](https://github.com/openshift-scale)
- [Model Context Protocol](https://github.com/modelcontextprotocol)

---

Built with ❤️ by the OpenShift Performance Scale Team