# Contributing to EntroFeed

Thank you for your interest in contributing to EntroFeed!

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- Docker & Docker Compose (for containerized development)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/entrofeed/entrofeed.git
cd entrofeed

# Install dependencies (frontend + backend)
cd app/frontend && npm install && cd ../..
uv pip install -e .

# Start backend (port 8001)
uv run server

# Start frontend (port 5174) - in another terminal
cd app/frontend && npm run dev
```

### Development with Docker

```bash
# Build and run in development mode
docker compose up --build

# View logs
docker compose logs -f
```

## Project Structure

```
entrofeed/
├── app/
│   ├── frontend/          # React frontend (Vite + TypeScript)
│   ├── agents/           # AI agent implementation
│   ├── llm/              # LLM provider handlers
│   ├── notification/     # Notification handlers
│   ├── ontology/         # Interest ontology system
│   ├── recommender/      # Recommendation engine
│   ├── storage/          # Storage backends
│   ├── app.py            # FastAPI application
│   ├── backend.py        # Core backend logic
│   └── rss.py            # RSS/Atom parsing
├── configs/              # Configuration files
├── data/                 # Data storage (gitignored)
├── docs/                 # Documentation (i18n: en/, zh/)
└── tests/                # Test suite
```

## Coding Standards

### Python

- Follow PEP 8 style guidelines
- Use type hints where possible
- Run `pre-commit run --all-files` before committing

### Frontend (React/TypeScript)

- Use functional components with hooks
- Follow existing component patterns
- Run `npm run build` to verify no TypeScript errors

### Testing

EntroFeed has multiple test suites:

#### Unit Tests (Python/pytest)
```bash
# Run all unit tests
pytest -vvv -cov

# Run specific test file
pytest tests/unit/test_rss.py -vvv

# Run with coverage
pytest -vvv -cov
```

#### E2E Tests (Playwright)
```bash
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install --with-deps

# Run E2E tests
npm run test:e2e

# Run E2E tests in headed mode
npm run test:e2e:headed

# Run E2E tests with UI mode
npm run test:e2e:ui
```

#### Test Structure
```
tests/
├── unit/                  # Python unit tests
│   ├── test_api_endpoints.py    # API endpoint tests
│   ├── test_backend.py          # Backend logic tests
│   ├── test_handlers.py         # Handler tests
│   ├── test_models.py           # Model validation tests
│   ├── test_performance.py      # Performance tests
│   └── test_security.py         # Security tests
└── e2e/                   # Playwright E2E tests
    ├── navigation.spec.ts  # Navigation and UI flow tests
    └── api-flow.spec.ts    # API integration tests
```

## Making Changes

1. **Fork the repository** and create your branch from `main`
2. **Create a feature branch**: `git checkout -b feature/my-new-feature`
3. **Make your changes** and add tests
4. **Ensure tests pass**: `pytest -vvv -cov`
5. **Commit your changes** with clear, descriptive messages
6. **Push to your fork** and submit a Pull Request

### Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(agent): add session management for chat history

- Add ChatSessionManager class for JSON-based session persistence
- Add API endpoints for CRUD operations on sessions
- Update frontend Agent page to use session context

Closes #123
```

## Pull Request Process

1. Update documentation for any changed functionality
2. Add tests for new features
3. Ensure CI passes (all tests must green)
4. Request review from a maintainer
5. Once approved, squash and merge

## Docker Image Builds

The Docker image is automatically built and published via GitHub Actions:

- On push to `main`: builds `latest` tag
- On version tag (`v*`): builds version tag
- On PR: builds for testing only (not pushed to registry)

To build locally:

```bash
docker build . --tag entrofeed
docker run -p 8000:80 entrofeed
```

## Questions?

- Open an issue at https://github.com/entrofeed/entrofeed/issues
- Check the [documentation](docs/) for detailed guides

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
