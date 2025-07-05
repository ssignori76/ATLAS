# Contributing to ATLAS

Prima di tutto, grazie per l'interesse nel contribuire al progetto ATLAS! 🎉

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

Questo progetto aderisce al [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). 
Partecipando, ti impegni a rispettare questo codice.

## Getting Started

### Prerequisites

- Python 3.10+
- Git
- Proxmox VE access (per testing)

### Development Setup

1. **Fork e Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ATLAS.git
   cd ATLAS
   ```

2. **Setup Environment**
   ```bash
   python -m venv venv-dev
   source venv-dev/bin/activate  # Linux/macOS
   pip install -r requirements-dev.txt
   ```

3. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

4. **Verify Setup**
   ```bash
   pytest
   pylint atlas/
   mypy atlas/
   ```

## How to Contribute

### Types of Contributions

- 🐛 **Bug Reports** - Segnala bug con dettagli per riprodurli
- 💡 **Feature Requests** - Proponi nuove funzionalità
- 📝 **Documentation** - Migliora la documentazione
- 🔧 **Code** - Correggi bug o implementa feature
- 🧪 **Testing** - Aggiungi o migliora test

### Workflow

1. **Check Issues** - Cerca issue esistenti o creane uno nuovo
2. **Create Branch** - `git checkout -b feature/your-feature-name`
3. **Develop** - Implementa le modifiche seguendo gli standard
4. **Test** - Assicurati che tutti i test passino
5. **Commit** - Usa conventional commits
6. **Push** - `git push origin feature/your-feature-name`
7. **Pull Request** - Crea PR con descrizione dettagliata

## Coding Standards

### Python Code Style

- **Formatting**: Black (`black atlas/`)
- **Import Sorting**: isort (`isort atlas/`)
- **Linting**: Pylint (`pylint atlas/`)
- **Type Checking**: MyPy (`mypy atlas/`)

### Code Quality

```bash
# Run all quality checks
black atlas/
isort atlas/
pylint atlas/
mypy atlas/
bandit -r atlas/
```

### Documentation

- **Docstrings**: Google style per tutte le classi e funzioni pubbliche
- **Type Hints**: Obbligatori per tutti i parametri e return values
- **Comments**: Per logica complessa, non per codice ovvio

```python
def example_function(param1: str, param2: int) -> bool:
    """
    Esempio di funzione ben documentata.
    
    Args:
        param1: Descrizione del primo parametro
        param2: Descrizione del secondo parametro
        
    Returns:
        True se successo, False altrimenti
        
    Raises:
        ValueError: Se param1 è vuoto
        
    Example:
        >>> result = example_function("test", 42)
        >>> print(result)
        True
    """
    if not param1:
        raise ValueError("param1 cannot be empty")
    return len(param1) > param2
```

## Testing

### Test Structure

```
tests/
├── unit/           # Test unitari
├── integration/    # Test integrazione
├── fixtures/       # Dati test
└── conftest.py     # Configurazione pytest
```

### Writing Tests

```python
import pytest
from atlas.agents.data_collector import DataCollectorAgent

class TestDataCollectorAgent:
    """Test suite per DataCollectorAgent."""
    
    @pytest.fixture
    def agent(self):
        """Fixture per agent."""
        return DataCollectorAgent(config=mock_config)
    
    def test_collect_vm_count_valid(self, agent, monkeypatch):
        """Test raccolta numero VM valido."""
        monkeypatch.setattr('builtins.input', lambda _: '3')
        result = agent._collect_vm_count()
        assert result == 3
    
    def test_collect_vm_count_invalid(self, agent, monkeypatch):
        """Test gestione input non valido."""
        inputs = iter(['0', '51', '5'])
        monkeypatch.setattr('builtins.input', lambda _: next(inputs))
        result = agent._collect_vm_count()
        assert result == 5
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=atlas --cov-report=html

# Run specific test file
pytest tests/unit/test_data_collector.py

# Run with markers
pytest -m "not integration"  # Skip integration tests
pytest -m "integration"      # Only integration tests
```

## Pull Request Process

### Before Submitting

1. ✅ **Tests Pass**: `pytest`
2. ✅ **Code Quality**: `pylint atlas/` e `mypy atlas/`
3. ✅ **Formatting**: `black atlas/` e `isort atlas/`
4. ✅ **Security**: `bandit -r atlas/`
5. ✅ **Documentation**: Aggiornata se necessario

### PR Template

```markdown
## Description
Breve descrizione delle modifiche

## Type of Change
- [ ] Bug fix (non-breaking change)
- [ ] New feature (non-breaking change)
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests aggiunti/aggiornati
- [ ] Integration tests aggiunti/aggiornati
- [ ] Manual testing eseguito

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] Documentation updated
```

### Conventional Commits

Usa [Conventional Commits](https://www.conventionalcommits.org/) per messaggi commit:

```
feat: add new data validation agent
fix: resolve memory leak in orchestrator
docs: update API documentation
test: add integration tests for proxmox client
refactor: simplify configuration loading
style: fix formatting in utils module
```

## Issue Reporting

### Bug Reports

Usa il template per bug report:

```markdown
**Describe the bug**
Chiara descrizione del bug

**To Reproduce**
Steps per riprodurre:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Expected behavior**
Comportamento atteso

**Screenshots**
Screenshot se utili

**Environment:**
 - OS: [e.g. Ubuntu 20.04]
 - Python Version: [e.g. 3.10.5]
 - ATLAS Version: [e.g. 1.0.0]
 - Proxmox Version: [e.g. 7.2]

**Additional context**
Contesto aggiuntivo
```

### Feature Requests

```markdown
**Is your feature request related to a problem?**
Descrizione del problema

**Describe the solution you'd like**
Soluzione preferita

**Describe alternatives you've considered**
Alternative considerate

**Additional context**
Contesto aggiuntivo, screenshot, etc.
```

## Development Guidelines

### Architecture Principles

- **Single Responsibility**: Una classe = una responsabilità
- **Dependency Injection**: Inietta dipendenze nei costruttori
- **Interface Segregation**: Interfacce piccole e specifiche
- **Open/Closed**: Aperto per estensioni, chiuso per modifiche

### Error Handling

```python
# Good: Specific exceptions
class ATLASError(Exception):
    """Base exception for ATLAS."""

class ValidationError(ATLASError):
    """Validation failed."""

# Good: Context and details
try:
    result = validate_vm_config(config)
except ValidationError as e:
    logger.error(f"VM validation failed: {e}")
    raise
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Good: Structured logging
logger.info("Starting VM validation", extra={
    "vm_count": len(vm_specs),
    "user_id": user.id
})
```

## Release Process

1. **Version Bump**: Update `atlas/version.py`
2. **Changelog**: Update `CHANGELOG.md`
3. **Tag**: `git tag v1.0.0`
4. **Release**: Create GitHub release
5. **PyPI**: Publish to PyPI (automated)

## Getting Help

- 💬 **Discussions**: [GitHub Discussions](https://github.com/ssignori76/ATLAS/discussions)
- 🐛 **Issues**: [GitHub Issues](https://github.com/ssignori76/ATLAS/issues)
- 📧 **Email**: atlas-dev@example.com

---

**Grazie per aver contribuito a ATLAS! 🚀**
