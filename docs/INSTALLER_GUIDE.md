# BEI JI XING Agent - One-Click Installation Technical Guide

## Overview

This document provides detailed instructions for implementing the "one-command download and ready-to-use" feature for the BEI JI XING Agent.

## Technology Stack

| Dimension | Choice | Reason |
|-----------|--------|--------|
| Installer Script Language | Python | Cross-platform support, simple syntax, no additional dependencies for users |
| Repository Hosting | GitHub | World's largest code hosting platform, supports Raw file access |
| Dependency Management | pip + venv | Python standard toolchain, no additional dependencies |
| CI/CD | GitHub Actions | Deep integration with GitHub repositories, simple configuration |

## Environment Configuration

### Server Configuration

1. **Create GitHub Repository**
   ```bash
   # Create repository
   # Repository URL: https://github.com/954510662-bot/beijixing-Agent
   ```

2. **Configure GitHub Actions**
   - Ensure GitHub Actions is enabled for the repository
   - Configure `GITHUB_TOKEN` (configured by default)

3. **File Structure**
   ```
   beijixing-Agent/
   ├── installer.py          # One-click installer script
   ├── setup.py             # Python package configuration
   ├── pyproject.toml       # Project metadata
   ├── .github/workflows/   # CI/CD configuration
   └── beijixing/           # Core code
   ```

### Client Requirements

| Requirement | Version | Description |
|-------------|---------|-------------|
| Python | >= 3.12 | Core runtime environment |
| Git | >= 2.0 | Clone repository |
| pip | >= 23.0 | Install dependencies |
| Operating System | Linux/WSL | Recommended environment |

## Command Design

### One-Click Installation Command

```bash
# Using curl
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 -

# Using wget
wget -qO- https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 -

# With parameters
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 - --model custom-model
```

### Parameter Description

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--model` | Specify AI model name | BeiJiXing-7B |
| `--dir` | Installation directory | ~/beijixing-agent |
| `--no-test` | Skip installation test | false |
| `--help` | Show help information | - |

## Installation Flow Design

```
User executes command
    │
    ▼
┌──────────────────────────────┐
│ 1. Check Prerequisites       │
│    - Python version          │
│    - Git installation         │
│    - pip installation        │
│    - WSL environment check  │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ 2. Clone Repository         │
│    - git clone               │
│    - Handle existing dirs    │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ 3. Create Virtual Env       │
│    - python -m venv          │
│    - Handle existing venv   │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ 4. Install Dependencies     │
│    - pip install             │
│    - Handle version conflicts│
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ 5. Setup Command Aliases   │
│    - Create startup script  │
│    - Add to PATH           │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ 6. Test Installation       │
│    - Logo display           │
│    - Planner test          │
└──────────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ 7. Output Success Info    │
│    - Installation path      │
│    - Usage instructions    │
└──────────────────────────────┘
```

## Permission Settings

### File Permissions

```bash
# Startup script permission
chmod +x beijixing

# Directory permission
chmod 755 ~/beijixing-agent

# Log directory permission
chmod 755 ~/.beijixing/logs
```

### User Permissions

| Operation | Requires sudo | Description |
|-----------|---------------|-------------|
| Clone repository | No | Regular user |
| Create virtual env | No | Regular user |
| Install dependencies | No | Use venv isolation |
| Setup command aliases | No | User directory operations |
| Add to PATH | No | Modify user bashrc |

## Security Considerations

### Code Signing

```bash
# Generate GPG key
gpg --gen-key

# Sign installer script
gpg --sign installer.py

# User verification
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py.sig | gpg --verify
```

### Security Checks

| Check Item | Description | Implementation |
|------------|-------------|----------------|
| File integrity | Prevent script tampering | SHA256 checksum |
| Dependency verification | Prevent malicious dependencies | Dependency whitelist |
| Environment isolation | Prevent system pollution | Virtual environment |
| Network security | Prevent MITM attacks | HTTPS access |

## Testing & Verification

### Unit Tests

```python
# tests/test_installer.py
def test_check_prerequisites():
    assert check_prerequisites() == True

def test_clone_repository():
    assert clone_repository(REPO_URL, TEST_DIR) == True

def test_create_venv():
    assert create_venv(TEST_DIR) == True
```

### Integration Tests

```bash
# Test installation flow
python -m pytest tests/test_installer.py -v

# Test installed functionality
cd ~/beijixing-agent
source .venv/bin/activate
python -c "from core.planner import Planner; p=Planner(); print(p.generate_plan('test', {}))"
```

### User Experience Tests

| Test Scenario | Expected Result |
|---------------|-----------------|
| First-time installation | Successfully install and display Logo |
| Repeated installation | Correctly handle existing directories |
| Network interruption | Provide friendly error message |
| Insufficient permissions | Suggest permission upgrade |

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Python version too low | System Python < 3.12 | Upgrade Python or use pyenv |
| Git not installed | Missing git command | `sudo apt install git` |
| Network timeout | Network connection issue | Check network or use proxy |
| Permission denied | Insufficient file permissions | Check directory permissions |
| Dependency conflict | System package conflict | Use virtual environment |

### Log Recording

```python
# installer.py log configuration
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='installer.log'
)
```

## CI/CD Configuration

### GitHub Actions Workflow

```yaml
name: BEI JI XING Agent CI/CD

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-22.04
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - run: pip install -e .[dev]
    - run: python -m pytest tests/
    - run: python setup.py sdist bdist_wheel
    - uses: softprops/action-gh-release@v2
      with:
        files: |
          dist/*.tar.gz
          dist/*.whl
        tag_name: v${{ github.run_number }}
```

## Deployment Verification

### Post-Deployment Checks

```bash
# Verify installer.py is accessible
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | head -5

# Verify package can be downloaded
curl -sI https://github.com/954510662-bot/beijixing-Agent/releases/latest/download/beijixing-agent.tar.gz
```

### Version Management

| Version Type | Trigger Condition | Version Format |
|--------------|-------------------|----------------|
| Dev version | push to develop | v0.0.1-dev |
| Test version | push to main | v0.0.1-test |
| Production version | Create release | v1.0.0 |

## Performance Optimization

### Installation Speed Optimization

| Optimization | Method | Effect |
|-------------|--------|--------|
| Dependency caching | pip cache | Reduce duplicate downloads |
| Parallel installation | pip --parallel | Speed up dependency installation |
| Mirror source | Use China mirror | Solve slow network issues |

### Error Recovery

```python
# Resume from breakpoint
def install_dependencies(target_dir):
    venv_pip = os.path.join(target_dir, ".venv", "bin", "pip")
    
    # Retry mechanism
    for attempt in range(3):
        success, _ = run_cmd(f"{venv_pip} install -e .", cwd=target_dir)
        if success:
            return True
        print(f"Retrying attempt {attempt + 1}...")
    
    return False
```

## Extended Features

### Custom Installation Options

```bash
# Silent installation
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 - --silent

# Specify model
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 - --model gpt-4

# Specify installation directory
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 - --dir /opt/beijixing
```

### Upgrade Feature

```bash
# Auto upgrade
beijixing --upgrade

# Manual upgrade
cd ~/beijixing-agent
git pull
pip install -e .
```

## Summary

With the above design, users can complete the BEI JI XING Agent installation with just one command:

```bash
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 -
```

The entire process implements:
- ✅ One-click installation
- ✅ Environment detection
- ✅ Auto configuration
- ✅ Test verification
- ✅ Security assurance
- ✅ CI/CD integration
