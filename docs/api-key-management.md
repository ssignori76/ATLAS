# API Key Management Guide

This document explains how ATLAS handles API keys and URLs for various LLM providers.

## Overview

ATLAS supports multiple methods for configuring LLM API credentials:

1. **Configuration file** (atlas.yaml)
2. **Environment variables** (.env file or system environment)  
3. **Standard provider environment variables** (OPENAI_API_KEY, etc.)

## Supported LLM Providers

### OpenAI

**Configuration file (atlas.yaml):**
```yaml
llm:
  provider: "openai"
  api_key: "sk-your_openai_api_key_here"
  model_name: "gpt-4"
  api_base_url: "https://api.openai.com/v1"  # Optional, defaults to OpenAI
```

**Environment variables:**
```bash
# ATLAS-specific variables
export ATLAS_LLM_PROVIDER="openai"
export ATLAS_LLM_API_KEY="sk-your_openai_api_key_here"
export ATLAS_LLM_MODEL_NAME="gpt-4"

# Or use standard OpenAI variables (automatically detected)
export OPENAI_API_KEY="sk-your_openai_api_key_here"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # Optional
```

### Azure OpenAI

**Configuration file (atlas.yaml):**
```yaml
llm:
  provider: "azure"
  api_key: "your_azure_openai_api_key"
  azure_endpoint: "https://your-resource.openai.azure.com/"
  azure_deployment_name: "your-gpt-4-deployment"
  azure_api_version: "2024-02-15-preview"
```

**Environment variables:**
```bash
# ATLAS-specific variables
export ATLAS_LLM_PROVIDER="azure"
export ATLAS_LLM_API_KEY="your_azure_openai_api_key"
export ATLAS_LLM_AZURE_ENDPOINT="https://your-resource.openai.azure.com/"
export ATLAS_LLM_AZURE_DEPLOYMENT_NAME="your-gpt-4-deployment"

# Or use standard Azure variables (automatically detected)
export AZURE_OPENAI_API_KEY="your_azure_openai_api_key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
```

### Anthropic Claude

**Configuration file (atlas.yaml):**
```yaml
llm:
  provider: "anthropic"
  api_key: "sk-ant-your_anthropic_api_key_here"
  model_name: "claude-3-sonnet-20240229"
```

**Environment variables:**
```bash
export ATLAS_LLM_PROVIDER="anthropic"
export ATLAS_LLM_API_KEY="sk-ant-your_anthropic_api_key_here"
export ATLAS_LLM_MODEL_NAME="claude-3-sonnet-20240229"
```

### Local Models (Ollama, etc.)

**Configuration file (atlas.yaml):**
```yaml
llm:
  provider: "local"
  api_base_url: "http://localhost:11434/v1"  # Ollama
  model_name: "llama2"
  local_api_port: 11434
```

**Environment variables:**
```bash
export ATLAS_LLM_PROVIDER="local"
export ATLAS_LLM_API_BASE_URL="http://localhost:11434/v1"
export ATLAS_LLM_MODEL_NAME="llama2"
```

## Configuration Priority

ATLAS loads configuration in the following order (later values override earlier ones):

1. **Default values** (hardcoded in configuration classes)
2. **Configuration file** (atlas.yaml)
3. **Environment variables** (ATLAS_LLM_* variables)
4. **Standard provider variables** (OPENAI_API_KEY, AZURE_OPENAI_*, etc.)

## Security Best Practices

### 1. Environment Variables (Recommended)

Store API keys in environment variables or .env files:

```bash
# .env file
ATLAS_LLM_PROVIDER=openai
ATLAS_LLM_API_KEY=sk-your_secret_key_here
ATLAS_LLM_MODEL_NAME=gpt-4
```

### 2. Configuration Files

If using configuration files, ensure proper file permissions:

```bash
# Make config file readable only by owner
chmod 600 atlas.yaml
```

**Never commit configuration files with API keys to version control!**

### 3. Production Deployment

For production environments:

- Use secure secret management (HashiCorp Vault, Azure Key Vault, AWS Secrets Manager)
- Set environment variables in your deployment system
- Use IAM roles and service principals where possible
- Rotate API keys regularly

## Configuration Examples

### Development Setup

Create a `.env` file in your project directory:

```bash
# Proxmox connection
ATLAS_PROXMOX_HOST=proxmox.local
ATLAS_PROXMOX_USER=root@pam
ATLAS_PROXMOX_PASSWORD=your_password

# LLM configuration
ATLAS_LLM_PROVIDER=openai
ATLAS_LLM_API_KEY=sk-your_openai_key_here
ATLAS_LLM_MODEL_NAME=gpt-4
ATLAS_LLM_TEMPERATURE=0.7

# System settings
ATLAS_LOG_LEVEL=DEBUG
ATLAS_WORK_DIR=~/.atlas
```

### Production Setup

Use a minimal configuration file for non-sensitive settings:

```yaml
# atlas.yaml (production)
llm:
  provider: "azure"  # Provider set in config
  model_name: "gpt-4"
  temperature: 0.5
  max_tokens: 4000

vm_defaults:
  memory: 4096
  cores: 4
  disk_size: "50G"

system:
  log_level: "INFO"
  backup_configs: true
```

Then set sensitive values via environment variables:

```bash
# Set via deployment system
export ATLAS_LLM_API_KEY="secret_from_vault"
export ATLAS_LLM_AZURE_ENDPOINT="https://company.openai.azure.com/"
export ATLAS_LLM_AZURE_DEPLOYMENT_NAME="gpt-4-prod"
export ATLAS_PROXMOX_TOKEN_VALUE="secret_token"
```

## Validation and Error Handling

ATLAS automatically validates LLM configuration at startup:

- **Missing API keys**: Clear error messages indicating which environment variables to set
- **Invalid endpoints**: Connection validation before first use
- **Provider availability**: Checks for required packages (openai, anthropic, etc.)

## Usage in Code

```python
from atlas.core import get_llm_client, create_completion

# Get configured LLM client
client = get_llm_client()

# Create a completion
response = create_completion([
    {"role": "user", "content": "Generate Terraform configuration for a web server VM"}
])

print(response["content"])
```

## Troubleshooting

### Common Issues

1. **"API key is required" error**
   - Check that environment variables are set correctly
   - Verify .env file is in the correct location
   - Ensure no typos in variable names

2. **"Package not installed" error**
   - Install required packages: `pip install openai anthropic`
   - Check requirements.txt includes all LLM dependencies

3. **Azure OpenAI authentication fails**
   - Verify all three required values: api_key, azure_endpoint, azure_deployment_name
   - Check endpoint URL format (should end with /)
   - Confirm deployment name matches Azure resource

4. **Local model connection fails**
   - Ensure local model server is running
   - Check port and URL configuration
   - Verify model name is available in local server

### Debug Configuration

Enable debug logging to see configuration loading:

```bash
export ATLAS_LOG_LEVEL=DEBUG
```

This will show:
- Which configuration files are loaded
- Environment variable overrides
- LLM client initialization
- API validation results
