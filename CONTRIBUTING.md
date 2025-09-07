# Contributing to Nexion

Thanks for your interest in contributing to Nexion! This document provides guidelines for contributing to the project.

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/anthonypreza/nexion
   cd nexion
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   uv sync --group dev  # Install development dependencies including pre-commit and ruff
   ```

3. **Set up pre-commit hooks (REQUIRED):**
   ```bash
   pre-commit install
   ```

   This ensures code is automatically formatted and linted before each commit.

## Code Style and Quality

We use [Ruff](https://docs.astral.sh/ruff/) for both linting and formatting to maintain consistent code quality.

### Pre-commit Hooks

Pre-commit hooks are **required** and will:
- Run `ruff check --fix` to automatically fix linting issues
- Run `ruff format` to format code consistently
- Check for trailing whitespace and other common issues
- Validate YAML files

### Manual Commands

You can run these commands manually:

```bash
# Check for linting issues
ruff check

# Auto-fix linting issues
ruff check --fix

# Format code
ruff format

# Run all pre-commit hooks manually
pre-commit run --all-files
```

## Pull Request Process

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the existing code patterns

3. **Test your changes:**
   ```bash
   nexctl dev  # Test the development server
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   Pre-commit hooks will automatically run and format your code.

5. **Push and create a pull request:**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Quality Standards

- **Code must pass all pre-commit hooks** - commits will be rejected if hooks fail
- **Follow existing patterns** - look at similar code in the project for guidance
- **Add tests** where appropriate (test framework TBD)
- **Update documentation** if you change functionality

## Development Tips

- Use `nexctl dev` to run the development server
- Check the `CLAUDE.md` file for additional development guidance
- The project uses Python 3.10+ with modern async/await patterns
- Follow the existing modular architecture (core, adapters, providers, storage)

## Questions?

If you have questions about contributing, please:
1. Check existing issues and discussions
2. Create an issue for questions about the codebase
3. Follow the existing code patterns when in doubt

We appreciate your contributions to Nexion! 🚀
