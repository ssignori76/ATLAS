# Changelog

All notable changes to the ATLAS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# Changelog

All notable changes to the ATLAS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Step 1.3: Conversation State Management** - Complete implementation
  - `ConversationStateManager` for persistent conversation management
  - Multiple persistence backends: JSON files and SQLite database
  - Conversation pause/resume functionality with state validation
  - Conversation history tracking and context retention
  - In-memory caching with automatic eviction for performance
  - Cleanup operations for old completed/cancelled conversations
  - Comprehensive filtering and listing capabilities
  - Error handling for edge cases and invalid state transitions
- **Step 1.2: Agent Conversation Flows** - Complete implementation
  - `ConversationManager` for orchestrating multi-agent conversations
  - `ConversationContext` for tracking conversation state and data
  - `ConversationFlow` for defining workflow stages and transitions
  - Support for VM provisioning workflow with 6 stages:
    - Data Collection, Validation, Proxmox Config, Software Provision, Documentation, Completion
  - Comprehensive error handling and recovery mechanisms
  - Conversation lifecycle management (start, continue, complete, cancel)
  - Status monitoring and conversation listing capabilities
  - Flow transition validation and stage processing
- Comprehensive test suites for both conversation flows and state management
  - `tests/test_agent_conversations.py` - Step 1.2 validation
  - `tests/test_conversation_state.py` - Step 1.3 validation
- Complete MVP base structure implementation
- Professional CLI interface with Rich UI components
- Comprehensive configuration management system
- Structured error handling with custom exception hierarchy
- Development tooling setup (Black, Pylint, MyPy, Pytest)
- Package configuration with pyproject.toml
- Agent foundation structure for AutoGen integration
- LLM integration with multi-provider support (OpenAI, Azure, Anthropic, Local)
- Comprehensive API key management system
- Configuration examples and environment templates

### Changed
- Project structure reorganized for scalability
- Documentation moved to dedicated `docs/` directory
- Requirements consolidated and organized by purpose
- **BREAKING**: Documentation restructured following industry standards
- Root README simplified to project overview and quick start
- `docs/README.md` converted to documentation navigation hub
- Removed content duplication between README files

### Fixed
- AutoGen import issues in `atlas/__init__.py` (fixed class name casing)
- Decorator compatibility issues in conversation manager methods

## [0.1.0] - 2025-07-05

### Added
- Initial project setup and repository structure
- Complete requirements analysis and documentation
- AI-friendly development specifications
- README with comprehensive project overview
- Contributing guidelines and development setup
- Requirements documentation in dedicated directory

### Technical Implementation
- **Configuration System**: Pydantic-based config with YAML/JSON/ENV support
- **CLI Interface**: Click-based commands with Rich styling and interactive elements
- **Error Handling**: Custom exception hierarchy with context and error codes
- **Package Management**: Modern pyproject.toml with optional dependencies
- **Development Tools**: Pre-configured linting, formatting, and testing tools

### Project Structure
```
ATLAS/
├── atlas/                   # Core application package
│   ├── cli.py              # Command line interface
│   ├── core/               # Core functionality
│   │   ├── config.py       # Configuration management
│   │   └── exceptions.py   # Custom exceptions
│   └── agents/             # AutoGen agents (foundation)
├── docs/                   # Documentation
│   └── requirements/       # Requirements specifications
├── pyproject.toml          # Modern Python packaging
├── requirements*.txt       # Dependencies
├── CHANGELOG.md           # This file
├── CONTRIBUTING.md        # Development guidelines
└── README.md             # Project overview
```

### CLI Commands Available
- `atlas init` - Initialize configuration file
- `atlas validate` - Validate configuration
- `atlas provision` - Start VM provisioning workflow
- `atlas status` - Check system status
- `atlas destroy` - Destroy VMs (with safety checks)

### Configuration Features
- **Multi-source**: YAML files, environment variables, CLI overrides
- **Validation**: Automatic validation with descriptive error messages
- **Security**: Vault integration and credential encryption support
- **Flexibility**: Runtime overrides and debug modes

### Next Phase Ready
- Agent implementation framework prepared
- Type safety and documentation standards established
- Testing infrastructure configured
- CI/CD pipeline foundation ready

---

## Release Notes

### v0.1.0 - MVP Foundation
This release establishes the complete foundation for the ATLAS system. While the AutoGen agents are not yet implemented, all infrastructure, configuration management, CLI interface, and development tools are fully functional and ready for the next development phase.

**Key Achievements:**
- ✅ Professional CLI with full configuration management
- ✅ Robust error handling and validation
- ✅ Modern Python packaging and development setup
- ✅ Comprehensive documentation and contributing guidelines
- ✅ AI-friendly code structure and type safety
- ✅ Ready for AutoGen agent implementation

**Upcoming in v0.2.0:**
- AutoGen agents implementation
- Interactive VM parameter collection
- Proxmox API integration
- Terraform and Ansible generation
- End-to-end provisioning workflow
