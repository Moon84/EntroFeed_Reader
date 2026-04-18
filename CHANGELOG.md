# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [1.0.1] - 2026-04-17

### Added

- Plugin architecture (notification, content retrieval, storage handlers)
- Multi-select articles and function calling in AI agent
- Click-to-configure UI for handlers
- services/ and skills/ directories structure

### Changed

- Migrated rss.py to services/feed/
- Updated GitHub links to new repository
- Use .venv/bin paths in Makefile

### Fixed

- Ontology rating calculation
- Settings LLM display
- Three-column reader layout

## [0.3.1] - 2026-04-10

### Added

- Initial release
- RSS/Atom feed aggregation with automatic updates
- SQLite + ChromaDB storage backend
- LLM integration (DashScope, Ollama, OpenAI)
- Interest-based recommendations
- Trending content recommendations
- Similar article recommendations
- AI Assistant chat interface
- MCP server for external AI integration
- Docker Compose deployment
- Multi-language support (English, Chinese)
- Dark/Light theme support
- Article translation feature

[Unreleased]: https://github.com/Moon84/EntroFeed_Reader/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/Moon84/EntroFeed_Reader/releases/tag/v1.0.1
[0.3.1]: https://github.com/Moon84/EntroFeed_Reader/releases/tag/v0.3.1