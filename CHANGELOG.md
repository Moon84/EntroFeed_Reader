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

## [1.0.1] - 2026-04-18

### Added

- Plugin architecture (notification, content retrieval, storage handlers)
- Multi-select articles and function calling in AI agent
- Click-to-configure UI for handlers
- services/ and skills/ directories structure
- 8 LLM providers: OpenAI, DeepSeek, Zhipu, Moonshot, Baichuan, Tencent, DashScope, Ollama
- UnifiedNode model with backward compatibility for legacy fields
- NodeSource.to_tag_source() for enum conversion
- Documentation: PRD, Architecture, API, Database schema (docs/architecture/)

### Changed

- Migrated rss.py to services/feed/
- Updated GitHub links to new repository
- Use .venv/bin paths in Makefile
- UnifiedNode model_validator improved for cleaner source conversion
- InterestUpdater methods now accept list[InterestTag | UnifiedNode]

### Fixed

- Ontology rating calculation
- Settings LLM display
- Three-column reader layout
- LLM plugin null checks for completion.choices[0].message.content
- memory.py .value access for category and source fields
- tagging.py assert for llm_summarizer to help mypy
- 283 tests now pass (was some failures)

### Infrastructure

- mypy configured with module-level ignores for leniency
- ruff.toml linter configuration
- .gitignore updated for docs/, .claude/, frontend artifacts

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