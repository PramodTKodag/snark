# Contributing to Snark

Welcome to Snark -- Sarcasm as a Service. We appreciate your interest in contributing to this AI-powered humor API. Whether you are fixing a bug, adding a feature, or improving documentation, your contributions help make this project better for everyone.

This guide will walk you through the process of contributing to the project.

## Code of Conduct

All contributors are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before participating. We are committed to providing a welcoming and inclusive environment for everyone.

## How to Contribute

We follow a standard fork-and-pull-request workflow:

1. **Fork the repository** -- Navigate to [https://github.com/PramodTKodag/snark](https://github.com/PramodTKodag/snark) and click the "Fork" button to create your own copy.

2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/<your-username>/snark.git
   cd snark
   ```

3. **Add the upstream remote** so you can keep your fork in sync:
   ```bash
   git remote add upstream https://github.com/PramodTKodag/snark.git
   ```

4. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

5. **Make your changes**, commit them, and push to your fork:
   ```bash
   git push origin feat/your-feature-name
   ```

6. **Open a Pull Request** against the `main` branch of the upstream repository.

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Poetry (for dependency management)
- Docker and Docker Compose

### Getting Started

1. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

2. Copy the example environment file and configure it for your local setup:
   ```bash
   cp .env.example .env
   ```

3. Start the development environment using Docker:
   ```bash
   docker compose --profile dev up --build
   ```

4. Run the test suite to verify everything is working:
   ```bash
   poetry run pytest
   ```

## Code Standards

All contributions must meet the following quality standards. CI will enforce these checks, so please run them locally before submitting a pull request.

- **Black** -- All Python code must be formatted with Black.
  ```bash
  poetry run black .
  ```

- **isort** -- Imports must be sorted consistently.
  ```bash
  poetry run isort .
  ```

- **flake8** -- Code must pass linting with no errors.
  ```bash
  poetry run flake8
  ```

- **pytest** -- All tests must pass, and new functionality should include corresponding tests.
  ```bash
  poetry run pytest
  ```

## Commit Message Convention

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. Each commit message should be structured as follows:

```
<type>(<scope>): <short summary>

<optional body>

<optional footer>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation changes only |
| `style` | Code style changes (formatting, missing semicolons, etc.) |
| `refactor` | Code changes that neither fix a bug nor add a feature |
| `perf` | Performance improvements |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks, dependency updates, CI changes |

### Examples

```
feat(api): add /v1/wit/haiku endpoint for generating haikus
fix(rate-limit): correct IP extraction behind reverse proxy
docs(readme): update development setup instructions
test(roast): add edge case tests for empty name parameter
```

## Pull Request Guidelines

When opening a pull request, please follow these guidelines:

1. **Link to an issue** -- Reference the relevant GitHub issue in your PR description (e.g., "Closes #42"). If no issue exists, consider creating one first to discuss the change.

2. **Describe your changes** -- Provide a clear summary of what you changed and why. Include any relevant context that reviewers should know.

3. **Include tests** -- All new features and bug fixes must include appropriate test coverage. PRs without tests for new functionality will not be merged.

4. **Keep PRs focused** -- Each pull request should address a single concern. Avoid bundling unrelated changes together.

5. **Ensure CI passes** -- All automated checks (Black, isort, flake8, pytest) must pass before a PR will be reviewed.

6. **Update documentation** -- If your changes affect the public API or user-facing behavior, update the relevant documentation.

## Contributor License Agreement

By submitting a pull request to this repository, you agree to the following terms:

- Your contribution is your original work, and you have the right to submit it.
- You grant Pramod Kodag a perpetual, worldwide, non-exclusive, royalty-free license to use, reproduce, modify, distribute, sublicense, and otherwise exploit your contribution in any form and for any purpose.
- The project owner, Pramod Kodag, retains all rights to the Snark project, including the right to relicense or commercially distribute the project and all contributions.
- Your contribution may be included in derivative works or commercial products at the project owner's discretion.

For the full terms of the Contributor License Agreement, please refer to [CLA.md](CLA.md).

If you have questions about the CLA, please open an issue before submitting your contribution.

## Reporting Bugs

Found a bug? Please report it using [GitHub Issues](https://github.com/PramodTKodag/snark/issues).

When filing a bug report, include the following information:

- A clear and descriptive title.
- Steps to reproduce the issue.
- Expected behavior versus actual behavior.
- Environment details (OS, Python version, Docker version, etc.).
- Any relevant logs or error messages.
- If possible, a minimal reproducible example.

Please search existing issues before creating a new one to avoid duplicates.

## Feature Requests

Have an idea for a new feature? We would love to hear it. Open a [GitHub Issue](https://github.com/PramodTKodag/snark/issues) with the label `enhancement` and include:

- A clear description of the feature and the problem it solves.
- Any proposed API design or usage examples.
- Context on why this would be valuable to the project and its users.

Feature requests are reviewed regularly. While we cannot guarantee every request will be implemented, community input plays an important role in shaping the project's direction.

---

Thank you for contributing to Snark. Your time and effort help make this project better for the entire community.

Copyright (c) Pramod Kodag. All rights reserved.
