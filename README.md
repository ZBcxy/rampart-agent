# BeiJiXing Agent

> Your Intelligent AI Assistant for Linux Terminal

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Platform](https://img.shields.io/badge/platform-Linux-green.svg)
![Python](https://img.shields.io/badge/python-3.8+-yellow.svg)

## Overview

BeiJiXing Agent is a powerful AI agent designed for Linux terminal environments. It provides intelligent assistance through a command-line interface, featuring modular architecture, easy installation, and seamless integration with your workflow.

## Features

### 🎨 Visual Design
- Beautiful ASCII art logo display
- Multiple logo styles (default, minimal, box)
- Animated loading effects
- Version information panel
- Real-time status display

### 🚀 Core Capabilities
- **Intelligent CLI** - Interactive command-line interface
- **Module System** - Extensible architecture with hot-swappable modules
- **Memory Management** - Three-tier memory architecture
- **Performance Monitoring** - Real-time performance metrics
- **Exception Handling** - Comprehensive error management

### 📦 Module System
- `code_analysis` - Code quality and pattern analysis
- `web_search` - Web search capabilities
- `file_manager` - Advanced file operations
- `data_processing` - Data transformation and analysis
- `api_integration` - REST API client
- `monitoring` - System resource monitoring

## Installation

### One-Line Installation (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/install.sh | bash
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/954510662-bot/beijixing-Agent.git ~/.beijixing

# Run installation script
cd ~/.beijixing
bash install.sh
```

### After Installation

1. Restart your terminal or run:
   ```bash
   source ~/.bashrc
   ```

2. Start BeiJiXing Agent:
   ```bash
   beijixing
   ```

## Usage

### Quick Start

```bash
# Start interactive mode
beijixing

# Show help
beijixing --help

# Show version
beijixing --version

# Display logo
beijixing --logo
```

### Logo Display Options

```bash
# Default logo with animation
beijixing --logo

# Minimal style
beijixing --logo --style minimal

# Box style
beijixing --logo --style box

# Without animation
beijixing --logo --no-animate
```

### Module Management

```bash
# List all modules
beijixing config list

# Add a module
beijixing config add code_analysis

# Remove a module
beijixing config remove code_analysis

# Enable a module
beijixing config enable code_analysis

# Disable a module
beijixing config disable code_analysis

# Show module status
beijixing config status
beijixing config status code_analysis
```

### Version Upgrade

```bash
# Check for updates
beijixing upgrade

# Upgrade to latest version
beijixing upgrade --latest

# Show changelog
beijixing upgrade --changelog

# Rollback to previous version
beijixing upgrade --rollback
```

### Configuration

```bash
# Show configuration
beijixing --config

# List installed modules
beijixing --modules
```

## Architecture

```
BeiJiXing Agent
├── core/              # Core modules
│   ├── logo.py       # Logo display module
│   ├── planner/       # Planning engine
│   ├── executor/      # Execution engine
│   ├── memory/        # Memory management
│   ├── align/         # Alignment engine
│   ├── exceptions.py  # Exception handling
│   └── performance.py # Performance monitoring
├── cli/               # CLI interface
├── gateway/           # API gateway
├── skills/            # Skill definitions
├── tests/             # Test suite
└── docs/              # Documentation
```

## Configuration Files

- **Config Directory**: `~/.beijixing/`
- **Modules**: `~/.beijixing/modules/`
- **Logs**: `~/.beijixing/logs/`
- **Data**: `~/.beijixing/data/`
- **Backups**: `~/.beijixing/backups/`

## Requirements

### System Requirements
- Linux operating system
- Python 3.8 or higher
- Git
- pip3

### Optional Dependencies
- curl (for one-line installation)
- zsh (for enhanced shell support)

## Development

### Running Tests

```bash
cd ~/.beijixing
source venv/bin/activate
pytest tests/ -v
```

### Code Style

```bash
# Format code
black .

# Check code style
flake8 .
```

## Troubleshooting

### Common Issues

**Issue: `beijixing: command not found`**

Solution:
```bash
source ~/.bashrc
# or restart your terminal
```

**Issue: Python version error**

Solution:
```bash
python3 --version  # Check Python version
# Ensure Python 3.8+ is installed
```

**Issue: Permission denied**

Solution:
```bash
chmod +x ~/.local/bin/beijixing
chmod +x ~/.beijixing/install.sh
```

### Logs

Check logs at:
```bash
cat ~/.beijixing/logs/beijixing.log
```

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
- GitHub Issues: https://github.com/954510662-bot/beijixing-Agent/issues
- Documentation: https://github.com/954510662-bot/beijixing-Agent/wiki

## Acknowledgments

Inspired by:
- Claude Code
- OpenClaw
- Hermes Agent
- Codex

---

**BeiJiXing Agent** - Your Intelligent AI Assistant
