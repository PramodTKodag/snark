# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-21

### Added

- 28 wit endpoints covering humor, developer culture, and workplace comedy
- AI provider abstraction with support for Groq, Gemini, and Claude
- Automatic provider fallback on content filter blocks or failures
- Persona system with configurable prompts, tone, temperature, and token limits
- Mood modifier support (15 moods: sarcastic, angry, funny, dramatic, etc.)
- Response caching (5 min) and persona caching (1 hr) via Redis
- Anti-repetition logic to keep responses fresh
- IP-based rate limiting (50 requests/hour) via DRF AnonRateThrottle
- Full health check endpoint with DB, Redis, and provider status
- Swagger UI and OpenAPI schema via drf-spectacular
- Idempotent seed command for personas
- Docker setup with dev and prod profiles
- CI pipeline with linting (Black, isort, Flake8) and testing (pytest)

[0.1.0]: https://github.com/PramodTKodag/snark/releases/tag/v0.1.0
