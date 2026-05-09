# Contributing to RAG Validation System

Thank you for your interest in contributing to the RAG Validation System! We welcome contributions from the community.

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## How to Contribute

### 1. Fork and Clone
```bash
git clone https://github.com/yourusername/rag-validation-system.git
cd rag-validation-system
```

### 2. Set up Development Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

### 3. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 4. Make Changes
- Follow the existing code style
- Write tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 5. Commit Changes
```bash
git add .
git commit -m "feat: add your feature description"
```

### 6. Push and Create Pull Request
```bash
git push origin feature/your-feature-name
```

## Development Guidelines

### Code Style
- Use Black for code formatting
- Use isort for import sorting
- Follow PEP 8 guidelines
- Use type hints
- Write docstrings for all public functions

### Testing
- Write unit tests for all new functionality
- Maintain test coverage above 80%
- Run tests before committing: `pytest`
- Run linting: `pre-commit run --all-files`

### Documentation
- Update README.md for significant changes
- Add docstrings to new functions
- Update type hints
- Keep examples up to date

## Commit Message Format

We follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Testing
- `chore`: Maintenance

## Reporting Issues

When reporting bugs, please include:
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

## Feature Requests

For feature requests, please:
- Describe the problem you're trying to solve
- Explain why existing solutions don't work
- Provide examples of the desired functionality

## Security Issues

For security vulnerabilities, please email security@example.com instead of creating a public issue.

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (MIT).