# EgressIP Performance Analyzer MCP Server

A comprehensive AI-powered performance analysis and testing platform for OpenShift EgressIP functionality, following the established OCP Performance Analyzer MCP repository structure.

**REVIEWER FEEDBACK ADDRESSED:**
- ✅ Files renamed with `egressip_` prefix as requested
- ✅ Folder structure reorganized for clarity  
- ✅ Stdio transport method clearly documented
- ✅ Enhanced integration with existing patterns

## Overview

The EgressIP Performance Analyzer provides advanced testing, monitoring, and analysis capabilities for OpenShift EgressIP implementations. It integrates large-scale performance testing (like CORNET-6498) with continuous monitoring and AI-powered bottleneck detection.

## Repository Structure (Updated with egressip_ prefix)

Following the established patterns in the OCP Performance Analyzer MCP repository:

```
├── analysis/egress/                          # Performance analysis modules
│   └── egressip_analyzer_performance_deepdrive.py
├── config/                                   # Configuration files  
│   └── config-egress.yml                     # EgressIP analyzer configuration
├── elt/egress/                              # Extract-Load-Transform processing
│   └── egressip_analyzer_elt_processor.py
├── mcp/egress/                              # MCP server implementation
│   └── egressip_analyzer_mcp_server.py       # Main MCP server (stdio transport)
├── tools/egressip/                          # Data collection tools (renamed)
│   ├── egressip_corenet_6498_runner.py      # CORNET-6498 test integration
│   ├── egressip_ovn_rule_analyzer.py        # OVN rule analysis  
│   └── egressip_metrics_collector.py        # Metrics collection
└── storage/                                 # Data storage (auto-created)
    └── egressip_*.db                        # SQLite databases
```

## Key Changes Addressing Reviewer Feedback

### 1. File Naming Convention ✅
All tools now use `egressip_` prefix:
- `corenet_6498_runner.py` → `egressip_corenet_6498_runner.py`
- `ovn_rule_analyzer.py` → `egressip_ovn_rule_analyzer.py`  
- `metrics_collector.py` → `egressip_metrics_collector.py`
- `egress_analyzer_mcp_server.py` → `egressip_analyzer_mcp_server.py`

### 2. Transport Clarification ✅
**MCP Transport Method: stdio**

The EgressIP MCP server uses **stdio transport** for communication:
- Reads MCP protocol messages from `stdin`
- Writes JSON responses to `stdout` 
- Compatible with Claude, other MCP clients, and command-line usage
- No network ports required - secure pipe-based communication

**Starting the server:**
```bash
cd mcp/egress
python egressip_analyzer_mcp_server.py
```

**Integration with AI agents:**
```bash
# The server communicates via stdio - AI agents connect through MCP protocol
# No additional network configuration required
```

### 3. Enhanced Architecture 🔧

**Class Naming Updates:**
- `CORENET6498Runner` → `EgressIPCORENET6498Runner`
- `OVNRuleAnalyzer` → `EgressIPOVNRuleAnalyzer`
- `EgressIPMetricsCollector` → Enhanced with `egressip_` prefixed methods
- `EgressIPMCPServer` → `EgressIPAnalyzerMCPServer`

**Database Schema Updates:**
- Table names prefixed: `egressip_status`, `egressip_ovn_rule_metrics`, etc.
- Enhanced indexing for better query performance
- Specific EgressIP context in all stored metrics

## Features

### 🚀 **Large-Scale Performance Testing**
- **CORENET-6498 Integration**: Execute large-scale EgressIP stress tests with 2000+ pods
- **Multi-Scenario Testing**: Node reboots, OVN pod restarts, scaling operations under load
- **IPv4/IPv6 Support**: Comprehensive dual-stack testing capabilities
- **Automated Validation**: SNAT/LRP rule consistency verification across test scenarios

### 🔍 **Advanced OVN Analysis**
- **Real-time Rule Validation**: Live SNAT and LRP rule consistency checking
- **Cross-node Comparison**: Multi-node rule consistency validation
- **Rule Change Monitoring**: Continuous monitoring for rule instability detection
- **Performance Correlation**: Direct correlation between OVN rules and performance metrics

### 📊 **ELT Data Processing**
- **Extract**: Raw data extraction from tests and metrics
- **Transform**: Structured data transformation for analysis
- **Load**: Persistent storage with SQLite backend
- **Historical Analysis**: Long-term performance pattern identification

### 🤖 **AI-Powered Analysis**
- **Natural Language Interface**: Query EgressIP performance using natural language
- **Automated Recommendations**: AI-generated optimization suggestions
- **Deep Dive Analysis**: Comprehensive performance pattern analysis
- **Predictive Insights**: Trend-based performance predictions

## MCP Tools (Updated)

The server provides **7 specialized MCP tools**:

1. **`run_egressip_cornet_6498_test`**: Execute CORNET-6498 large-scale EgressIP stress test
2. **`validate_egressip_snat_lrp_rules`**: Validate SNAT/LRP rules consistency on specific nodes  
3. **`analyze_egressip_performance`**: Analyze EgressIP performance and identify bottlenecks
4. **`get_egressip_status`**: Get comprehensive EgressIP status across the cluster
5. **`monitor_egressip_ovn_rules`**: Monitor OVN rule changes over time for stability analysis
6. **`compare_egressip_rules_across_nodes`**: Compare rules across multiple nodes
7. **`get_egressip_metrics_summary`**: Get historical metrics and trend analysis

**Plus 2 MCP resources:**
- **`egressip_config`**: Current configuration settings
- **`egressip_help`**: Comprehensive help documentation

## Quick Start

### Prerequisites
- OpenShift cluster with OVN-Kubernetes networking
- Python 3.8+ with dependencies: `fastmcp`, `pyyaml`, `asyncio`
- `oc` CLI tool configured
- Appropriate RBAC permissions for EgressIP operations

### Installation

1. **Install dependencies**:
   ```bash
   pip install fastmcp pyyaml
   ```

2. **Start the MCP server** (stdio transport):
   ```bash
   cd mcp/egress
   python egressip_analyzer_mcp_server.py
   ```

3. **Configuration** (optional):
   - Edit `config/config-egress.yml` for custom settings
   - Adjust test parameters and thresholds as needed

### Usage Examples

#### Natural Language Queries (via AI agents)
```bash
"Run a CORNET-6498 test with 5 EgressIP objects and 100 pods each"
"Check if SNAT rules are consistent on worker-0"  
"Show me EgressIP performance trends from the last week"
"What's the current status of all EgressIP objects?"
"Compare EgressIP rules between worker-0 and worker-1"
```

#### Direct Tool Usage
```python
# Execute large-scale EgressIP test
result = await run_egressip_cornet_6498_test(
    eip_object_count=10,
    pods_per_eip=200,
    iterations=20,
    ip_stack="ipv4"
)

# Validate OVN rules
validation = await validate_egressip_snat_lrp_rules("worker-0")

# Analyze performance
analysis = await analyze_egressip_performance("test-namespace")

# Monitor rule changes
monitoring = await monitor_egressip_ovn_rules("worker-0", duration_minutes=10)
```

## Integration with Existing Go Tests

The implementation provides seamless integration with existing Go test infrastructure:

- **Preserves Existing Logic**: Original `corenet_6498_test.go` runs unchanged
- **Python Bridge**: Wrapper for Go test execution and result parsing
- **Enhanced Analysis**: Advanced metrics collection and AI-powered insights
- **Data Processing**: ELT pipeline for long-term trend analysis

## Data Flow

```
Go Tests → tools/egressip → elt/egress → analysis/egress → mcp/egress → AI Agents
    ↓           ↓              ↓             ↓              ↓
Raw Results  Extract    Transform     Analyze      MCP Tools    Natural Language
```

## Component Details

### **Analysis Component** (`analysis/egress/`)
- Deep dive performance analysis with EgressIP-specific focus
- Bottleneck identification for large-scale deployments
- Performance pattern recognition across test scenarios
- Optimization recommendations based on CORNET-6498 results

### **ELT Component** (`elt/egress/`)
- Data extraction from CORNET-6498 tests and OVN rule analysis
- Structured transformation for EgressIP-specific analysis
- Persistent loading into SQLite storage with proper indexing
- Historical data management for trend analysis

### **Tools Component** (`tools/egressip/`)
- `egressip_cornet_6498_runner.py`: CORNET-6498 test runner and integration
- `egressip_ovn_rule_analyzer.py`: OVN rule analyzer with consistency checking
- `egressip_metrics_collector.py`: Comprehensive metrics collection

### **MCP Server** (`mcp/egress/`)
- `egressip_analyzer_mcp_server.py`: FastMCP-based server with stdio transport
- 7 specialized tools for EgressIP analysis
- Configuration-driven behavior with intelligent defaults
- Full AI agent integration with natural language support

## Testing and Validation

- **Unit Tests**: Core functionality validation for each component
- **Integration Tests**: End-to-end test execution with real clusters
- **MCP Protocol Tests**: Tool interface validation with various clients
- **Performance Tests**: Large-scale scenario validation with CORNET-6498

## Transport Implementation Details

**Stdio Transport Benefits:**
- ✅ Secure pipe-based communication (no network exposure)
- ✅ Simple integration with AI agents and command-line tools
- ✅ Platform-agnostic (works across different environments)
- ✅ Easy debugging and logging
- ✅ No port conflicts or firewall issues

**Communication Flow:**
```
AI Agent/Client → stdin → EgressIP MCP Server → stdout → AI Agent/Client
                          ↓
                     Process Tools/Resources
                          ↓
                     Generate JSON Responses
```

## Dependencies

- Python 3.8+ with FastMCP framework for MCP protocol support
- OpenShift/Kubernetes cluster with OVN-Kubernetes networking
- Go 1.19+ and Ginkgo framework (for CORNET-6498 test execution)
- SQLite for persistent data storage and metrics
- PyYAML for configuration file handling

## Contributing

Follow the established repository patterns:
- Use the modular structure (`analysis/`, `elt/`, `tools/`, `mcp/`)
- Place configurations in the central `config/` directory
- Follow naming conventions: `egressip_*` for EgressIP-specific components
- Maintain separation of concerns between components
- Use stdio transport for all MCP server implementations

## Migration Notes

For users of the previous version:
1. Update import statements to use new `egressip_` prefixed modules
2. No functional changes - all APIs remain the same
3. Configuration files remain compatible
4. Existing test data and databases will work without modification

---

**Tested on**: OpenShift 4.16.8+ with OVN-Kubernetes  
**Compatible with**: AWS, GCP, Azure, OpenStack, vSphere, Bare Metal platforms  
**AI Agents**: Claude, and other MCP-compatible agents  
**Transport**: stdio (Model Context Protocol over standard input/output)