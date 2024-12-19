# RTL433-HA Documentation

## Documentation Structure

- `DEVELOPMENT.md` - Comprehensive development guide
- `INSTALLATION.md` - Installation instructions for users
- `TROUBLESHOOTING.md` - Common issues and solutions
- `API.md` - Component API documentation
- `PROTOCOLS.md` - Supported device protocols
- `CONTRIBUTING.md` - Guidelines for contributors

## Project Structure

```
rtl433-ha/
├── src/                    # Source code
│   └── custom_components/  # Home Assistant component
│       └── rtl433/        # RTL-433 integration
├── tests/                  # Test suite
├── docs/                   # Documentation
├── tools/                  # Development tools
│   └── debug.sh           # Development environment launcher
└── config/                # Test configuration
```

## Development Setup

Two methods are available for development:

### Method 1: Development Install (Recommended)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
tools/debug.sh
```

### Method 2: Direct Copy
```bash
python -m venv .venv
source .venv/bin/activate
INSTALL_METHOD=copy tools/debug.sh
```

## Documentation Guidelines

1. Keep documentation up to date with code changes
2. Use markdown for all documentation
3. Include code examples where appropriate
4. Maintain separate files for different concerns
5. Include troubleshooting sections 