# Jenkins MCP Server

A comprehensive Model Context Protocol (MCP) server for Jenkins automation that provides programmatic access to nearly all Jenkins UI functionality through MCP tools, resources, and prompts.

## Features

### 🔧 Comprehensive Jenkins Management
- **Job Management**: Create, update, configure, enable/disable, and delete Jenkins jobs
- **Build Management**: Trigger builds, monitor progress, retrieve logs, and manage artifacts
- **System Monitoring**: Get system information, monitor nodes, and track performance
- **View Management**: Organize jobs into views and manage view configurations
- **Credential Management**: Securely manage Jenkins credentials
- **User Management**: Handle user accounts and permissions

### 🚀 Modern Architecture
- **FastMCP 2**: Built on the latest MCP framework for optimal performance
- **Async Operations**: Full async/await support for concurrent operations
- **Error Handling**: Comprehensive retry logic and graceful error recovery
- **Structured Logging**: Detailed logging with multiple output formats
- **Multiple Authentication**: Support for API tokens, basic auth, and OAuth

### 📊 Rich Resources and Prompts
- **Configuration Resources**: Access system, job, view, and node configurations
- **Status Resources**: Real-time system and build status information
- **Log Resources**: Progressive log streaming and historical access
- **Automation Prompts**: Guidance for CI/CD pipeline setup and optimization
- **Troubleshooting Prompts**: Step-by-step diagnostic workflows

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/jenkins-mcp.git
cd jenkins-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

### Configuration

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Edit `.env` with your Jenkins credentials:
```bash
JENKINS_URL=http://your-jenkins:8080
JENKINS_USER=your-username
JENKINS_TOKEN=your-api-token
JENKINS_AUTH_METHOD=API_TOKEN
```

### Running the Server

```bash
# Start the MCP server
python -m jenkins_mcp.server

# Or use the installed script
jenkins-mcp-server
```

## Available Tools

### Job Management
- `list_jobs` - List Jenkins jobs with filtering
- `get_job_details` - Get comprehensive job information
- `create_job` - Create new jobs from configuration
- `update_job_config` - Update existing job configurations
- `delete_job` - Remove jobs with confirmation
- `enable_job` / `disable_job` - Control job execution
- `copy_job` - Create job copies
- `get_job_config` - Retrieve job configurations

### Build Management
- `trigger_build` - Trigger builds (simple and parameterized)
- `get_build_details` - Get comprehensive build information
- `get_build_log` - Retrieve build logs with streaming
- `get_build_artifacts` - List and download build artifacts
- `abort_build` - Cancel running builds
- `get_build_queue` - Check build queue status
- `get_build_history` - Get historical build data

### System Monitoring
- `get_system_info` - Jenkins system information
- `get_version` - Jenkins version details
- `list_nodes` - List Jenkins agents/nodes
- `get_node_details` - Detailed node information
- `get_plugin_list` - Plugin inventory and status
- `get_load_statistics` - System performance metrics

### View Management
- `list_views` - List all Jenkins views
- `get_view_details` - Get detailed view information
- `create_view` - Create new views
- `update_view` - Modify existing views

### Credential Management
- `list_credentials` - Browse credential stores
- `create_credential` - Add new credentials
- `update_credential` - Modify existing credentials
- `delete_credential` - Remove credentials

### User Management
- `get_user_info` - Current user details
- `list_users` - Browse Jenkins users
- `create_user` - Create new user accounts

## Available Resources

- `jenkins://config/system` - System configuration
- `jenkins://config/jobs/{job_name}` - Job configurations
- `jenkins://status/system` - Current system status
- `jenkins://status/builds/{job_name}/{build_number}` - Build status
- `jenkins://logs/builds/{job_name}/{build_number}` - Build logs
- `jenkins://data/artifacts/{job_name}/{build_number}` - Build artifacts

## Available Prompts

- `jenkins_automation_setup` - CI/CD workflow guidance
- `build_pipeline_design` - Pipeline architecture design
- `job_template_creation` - Reusable job templates
- `build_failure_analysis` - Troubleshooting failed builds
- `performance_diagnostics` - System performance analysis
- `git_integration_setup` - Source control integration

## Examples

### Basic Usage

```python
# List all jobs
jobs = await list_jobs(include_details=True)

# Trigger a build with parameters
build_result = await trigger_build(
    job_name="my-app",
    parameters={"ENVIRONMENT": "staging", "BRANCH": "main"}
)

# Get build details
build_info = await get_build_details(
    job_name="my-app",
    build_number=build_result["build_number"]
)

# Monitor build progress
logs = await get_build_log(
    job_name="my-app",
    build_number=build_result["build_number"],
    follow=True
)
```

### Advanced Workflow

```python
# Create a new job from template
await create_job(
    job_name="my-new-app",
    config_xml=job_template_xml,
    from_template="template-web-app"
)

# Configure monitoring
system_status = await get_system_info()
load_stats = await get_load_statistics()

# Set up automated pipeline
pipeline_config = await mcp.prompt("build_pipeline_design")
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=jenkins_mcp --cov-report=html

# Run specific tests
pytest tests/test_tools.py -v
```

### Code Quality

```bash
# Format code
black jenkins_mcp/

# Lint code
ruff check jenkins_mcp/

# Type checking
mypy jenkins_mcp/
```

## Docker Support

```bash
# Build Docker image
docker build -t jenkins-mcp-server .

# Run with environment variables
docker run -d \
  --name jenkins-mcp \
  -e JENKINS_URL="http://jenkins:8080" \
  -e JENKINS_USER="admin" \
  -e JENKINS_TOKEN="your-token" \
  jenkins-mcp-server
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JENKINS_URL` | Jenkins server URL | Required |
| `JENKINS_USER` | Jenkins username | Required |
| `JENKINS_TOKEN` | API token or password | Required |
| `JENKINS_AUTH_METHOD` | Auth method (API_TOKEN, BASIC, OAUTH) | API_TOKEN |
| `JENKINS_TIMEOUT` | Request timeout (seconds) | 30 |
| `JENKINS_RETRY_COUNT` | Number of retries | 3 |
| `MCP_SERVER_LOG_LEVEL` | Logging level | INFO |
| `MCP_SERVER_JSON_LOGS` | JSON logging format | false |

### Authentication Methods

1. **API Token (Recommended)**: Use Jenkins user API tokens
2. **Basic Auth**: Username/password authentication
3. **OAuth**: Enterprise OAuth 2.0 integration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [Full documentation](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/jenkins-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/jenkins-mcp/discussions)

## Changelog

### v1.0.0
- Initial release
- Comprehensive Jenkins API coverage
- FastMCP 2 integration
- Multiple authentication methods
- Full async support
- Structured logging and error handling
- Docker and Kubernetes support