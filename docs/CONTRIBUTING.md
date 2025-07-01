# Contributing to Contextly

First off, thank you for considering contributing to Contextly! It's people like you that make Contextly such a great tool.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct:
- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed after following the steps**
- **Explain which behavior you expected to see instead and why**
- **Include screenshots and animated GIFs if possible**

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the steps**
- **Describe the current behavior and explain which behavior you expected to see instead**
- **Explain why this enhancement would be useful**

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the existing style
6. Issue that pull request!

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/contextly.git
   cd contextly
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

3. **Set up Node environment (for extension development)**
   ```bash
   npm install
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Style Guides

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

### JavaScript Style Guide

- Use ES6+ features
- 2 spaces for indentation
- Use semicolons
- Use single quotes for strings
- Add trailing commas in multi-line objects/arrays

### Python Style Guide

- Follow PEP 8
- Use type hints where possible
- Write docstrings for all functions and classes
- Use f-strings for string formatting

## Project Structure Guidelines

### Extension Code
- Keep content scripts focused and platform-specific
- Use message passing for communication between components
- Minimize permissions requested in manifest.json

### Backend Code
- Keep endpoints RESTful and well-documented
- Use dependency injection for services
- Write comprehensive error handling
- Add logging for debugging

## Testing

### Running Tests

```bash
# Python tests
pytest

# JavaScript tests
npm test

# Linting
npm run lint
pylint src/
```

### Writing Tests

- Write unit tests for all new functionality
- Aim for >80% code coverage
- Test edge cases and error conditions
- Use meaningful test names that describe what is being tested

## Documentation

- Update README.md if you change functionality
- Add JSDoc comments to JavaScript functions
- Add docstrings to Python functions
- Update API documentation for new endpoints

## Release Process

1. Update version in `manifest.json` and `package.json`
2. Update CHANGELOG.md
3. Create a pull request with version bump
4. After merge, tag the release
5. Build and package the extension

## Questions?

Feel free to open an issue with your question or reach out on our Discord server.

Thank you for contributing! 🎉