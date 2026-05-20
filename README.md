# BEI JI XING Agent

A powerful AI Agent framework inspired by leading agents like Claude Code, OpenAI Models, and Hermes Agent.

## 🚀 Quick Start

### One-Click Installation

```bash
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 -
```

Or using wget:

```bash
wget -qO- https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 -
```

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/954510662-bot/beijixing-Agent.git
cd beijixing-Agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Run the agent
python cli/agent_cli.py
```

## ✨ Features

### Core Functionality
- **Natural Language Understanding**: Advanced NLU capabilities for complex command parsing
- **Multi-turn Conversation**: Seamless context retention across dialogue sessions
- **Tool Integration**: Extensible tool framework for external API integration
- **Planning Engine**: Intelligent task decomposition and planning

### Memory System
- **Working Memory**: Short-term context management
- **Episodic Memory**: Long-term interaction history storage
- **Semantic Memory**: Knowledge base with keyword indexing

### Security & Compliance
- **Sandbox Execution**: Secure code execution environment
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: Built-in request throttling

## 🏗️ Architecture

```
beijixing/
├── core/                # Core engine modules
│   ├── planner/         # Planning engine
│   ├── executor/        # Task executor with sandbox
│   ├── memory/          # Three-tier memory system
│   ├── align/           # Alignment and arbitration
│   └── ...
├── gateway/             # API gateway
├── cli/                 # Command-line interface
├── tests/               # Test suites
└── docs/                # Documentation
```

## 📖 Documentation

- [Technical Documentation](docs/TECHNICAL_DOCUMENTATION.md)
- [User Manual](docs/USER_MANUAL.md)
- [Optimization Plan](docs/OPTIMIZATION_PLAN.md)

## 🔧 Usage

### Command Line Interface

```bash
# Interactive mode
beijixing

# Run specific task
beijixing "Analyze sales data and generate report"

# Memory management
beijixing memory search "keyword"
beijixing memory add "important information"

# Help
beijixing --help
```

### API Mode

```bash
# Start API server
python -m gateway.main

# Access API
curl http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, agent!"}'
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run unit tests
python -m pytest tests/unit/ -v

# Run integration tests
python -m pytest tests/integration/ -v

# Run with coverage
python -m pytest tests/ -v --cov=beijixing
```

## 🛠️ Development

### Prerequisites
- Python 3.12+
- Git
- WSL Ubuntu 22.04+ (recommended)

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/954510662-bot/beijixing-Agent.git
cd beijixing-Agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -e .[dev]

# Setup pre-commit hooks
pre-commit install
```

### Code Formatting

```bash
# Format code with Black
black .

# Sort imports with isort
isort .

# Lint with Flake8
flake8 .
```

## 📊 Performance

| Module | Average Time | P99 Time |
|--------|--------------|----------|
| Plan Generation | 0.39 ms | 0.69 ms |
| Working Memory Write | 0.43 ms | - |
| Semantic Memory Search | 0.10 ms | - |
| Confidence Evaluation | 0.01 ms | - |

## ❓ FAQ

### Q: How to install on Windows?

**A:** We recommend using WSL (Windows Subsystem for Linux) for the best experience:

```bash
# Install WSL
wsl --install -d Ubuntu-22.04

# Then run the one-click installer inside WSL
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 -
```

### Q: How to update the agent?

**A:** Run the installer again or pull the latest changes:

```bash
cd ~/beijixing-agent
git pull
pip install -e .
```

### Q: How to add custom tools?

**A:** Create a tool module in `core/executor/tools/` and register it in `tool_registry.py`.

### Q: How to change the AI model?

**A:** Set the `BEIJIXING_MODEL` environment variable:

```bash
export BEIJIXING_MODEL="custom-model-7B"
beijixing
```

### Q: How to enable API access?

**A:** Start the gateway server:

```bash
python -m gateway.main --host 0.0.0.0 --port 8000
```

## 📝 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📧 Contact

For support or inquiries, please open an issue on GitHub.

---

**BEI JI XING Agent** - Empowering AI-powered automation

---

## 🚀 One-Click Installation (Short Version)

```bash
curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 -
```
