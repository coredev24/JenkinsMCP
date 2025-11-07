"""
Jenkins automation MCP prompts.

Provides guidance for setting up automated workflows and CI/CD pipelines.
"""


def automation_setup() -> str:
    """Guide for setting up Jenkins automation workflows."""
    return """# Jenkins Automation Setup Guide

## Overview
This prompt helps you design and implement automated CI/CD workflows in Jenkins.

## Assessment Questions
1. What type of application are you building? (web app, mobile app, library, etc.)
2. What source control system are you using? (Git, SVN, etc.)
3. What are your deployment targets? (development, staging, production)
4. What testing frameworks do you use?
5. What deployment strategy do you prefer? (blue-green, canary, rolling)

## Workflow Components to Configure
- [ ] Source code repository integration
- [ ] Build triggers (webhooks, scheduled, manual)
- [ ] Build environment setup
- [ ] Test execution and reporting
- [ ] Artifact management
- [ ] Deployment pipeline stages
- [ ] Notification and alerting
- [ ] Rollback strategies

## Recommended Tools and Plugins
- Git Plugin or appropriate SCM plugin
- Pipeline Plugin (for Jenkinsfile)
- Blue Ocean Plugin (for pipeline visualization)
- Credentials Plugin (for secure credential storage)
- Email Extension Plugin (for notifications)
- Deploy Plugin (for application deployment)
- Slack Plugin (for team notifications)

## Example Pipeline Stages
1. Code Checkout
2. Environment Setup
3. Build Application
4. Run Tests
5. Code Quality Checks
6. Security Scanning
7. Artifact Creation
8. Deploy to Target Environment
9. Integration Tests
10. Rollback (if needed)

## Next Steps
1. Create pipeline configuration (Jenkinsfile or UI config)
2. Set up build triggers
3. Configure credentials
4. Test the pipeline
5. Monitor and optimize

Use the Jenkins MCP tools to implement each of these components.
"""


def pipeline_design() -> str:
    """Guide for designing CI/CD build pipelines."""
    return """# Build Pipeline Design Guide

## Pipeline Architecture
Design your build pipeline with the following considerations:

### Stage Design Principles
- **Fast Feedback**: Quick stages first (linting, unit tests)
- **Parallel Execution**: Independent stages run in parallel
- **Fail Fast**: Stop pipeline on first failure
- **Idempotent**: Stages can be re-run safely
- **Observable**: Clear logging and status reporting

### Standard Pipeline Template
```groovy
pipeline {
    agent any

    stages {
        stage('Preparation') {
            steps {
                // Checkout code, setup environment
            }
        }

        stage('Quality Checks') {
            parallel {
                stage('Linting') { /* lint code */ }
                stage('Security Scan') { /* security checks */ }
                stage('Unit Tests') { /* run unit tests */ }
            }
        }

        stage('Build') {
            steps {
                // Compile, package application
            }
        }

        stage('Integration Tests') {
            steps {
                // Run integration test suite
            }
        }

        stage('Deploy') {
            steps {
                // Deploy to target environment
            }
        }
    }

    post {
        always { /* cleanup, notifications */ }
        success { /* success notifications */ }
        failure { /* failure handling */ }
    }
}
```

### Environment Configuration
- **Development**: Fast builds, basic testing
- **Staging**: Full test suite, performance testing
- **Production**: Comprehensive checks, gradual rollout

### Artifact Strategy
- **Build Artifacts**: Compiled applications, Docker images
- **Test Reports**: JUnit, coverage reports
- **Documentation**: Generated API docs, changelogs
- **Deployment Packages**: Versioned release packages

### Monitoring and Observability
- Build duration and success metrics
- Test coverage trends
- Security scan results
- Performance benchmarks
- Rollback frequency

## Implementation Tools
- Use `create_job` to set up pipeline jobs
- Use `trigger_build` to test pipeline execution
- Use `get_build_details` to monitor pipeline runs
- Use `get_build_log` to troubleshoot failures
"""


def job_template_creation() -> str:
    """Guide for creating reusable Jenkins job templates."""
    return """# Jenkins Job Template Creation Guide

## Template Categories

### 1. Build Job Template
**Purpose**: Standard application build process
**Includes**:
- Source code checkout
- Dependency installation
- Build execution
- Artifact creation
- Basic test execution

### 2. Test Job Template
**Purpose**: Comprehensive testing suite
**Includes**:
- Test environment setup
- Unit test execution
- Integration test execution
- Code coverage reporting
- Test result publishing

### 3. Deployment Job Template
**Purpose**: Application deployment to environments
**Includes**:
- Artifact download
- Environment configuration
- Deployment execution
- Health checks
- Rollback capability

### 4. Maintenance Job Template
**Purpose**: System maintenance and cleanup
**Includes**:
- Log rotation
- Temporary file cleanup
- Cache clearing
- System health checks

## Template Structure
```xml
<project>
    <description>${JOB_DESCRIPTION}</description>
    <builders>
        <!-- Build steps with placeholders -->
    </builders>
    <publishers>
        <!-- Post-build actions -->
    </publishers>
    <properties>
        <!-- Job properties -->
    </properties>
    <parameters>
        <!-- Build parameters -->
    </parameters>
</project>
```

## Parameterization Strategy
- **${JOB_NAME}**: Job-specific name
- **${SOURCE_REPO}**: Source code repository
- **${BRANCH_NAME}**: Git branch to build
- **${BUILD_COMMAND}**: Custom build command
- **${TEST_COMMAND}**: Test execution command
- **${DEPLOY_TARGET}**: Deployment environment

## Template Management
1. Create template jobs with naming convention: `template-{category}`
2. Use `copy_job` to create jobs from templates
3. Customize parameters and configuration as needed
4. Maintain template versions and update strategies

## Best Practices
- Keep templates simple and focused
- Use clear parameter names and descriptions
- Document template usage and requirements
- Test templates thoroughly before reuse
- Regular maintenance and updates

## Implementation Steps
1. Design template structure
2. Create XML configuration with placeholders
3. Create template job using `create_job`
4. Document template usage
5. Test template with `copy_job`
6. Refine based on usage patterns
"""


def monitoring_setup() -> str:
    """Guide for setting up monitoring and alerting."""
    return """# Monitoring and Alerting Setup Guide

## Monitoring Components

### 1. Build Monitoring
- Build success/failure rates
- Build duration trends
- Queue wait times
- Resource utilization

### 2. System Health Monitoring
- Jenkins master health
- Agent node status
- Disk space usage
- Memory utilization
- Network connectivity

### 3. Security Monitoring
- Authentication failures
- Unauthorized access attempts
- Permission changes
- Configuration modifications

## Alerting Strategies

### Build Alerts
- Failed builds notification
- Long-running build alerts
- Queue overflow warnings
- Success rate thresholds

### System Alerts
- Node offline alerts
- High resource usage warnings
- Disk space alerts
- Service availability alerts

### Security Alerts
- Failed login attempts
- Permission escalations
- Configuration changes
- Plugin updates

## Implementation Tools
- Email Extension Plugin for email notifications
- Slack Plugin for team notifications
- Prometheus Plugin for metrics collection
- Logstash Plugin for log aggregation

## Configuration Steps
1. Install required monitoring plugins
2. Configure notification channels
3. Set up alert thresholds
4. Test alert delivery
5. Monitor and adjust thresholds

Use Jenkins MCP tools to set up and configure monitoring components.
"""