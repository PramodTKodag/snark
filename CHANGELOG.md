# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `GET /v1/wit/roast-url/` — roast any public URL, backed by an SSRF-hardened fetcher and Open Graph/metadata extraction (with matching CLI `url` command and `snark_roast_url` MCP tool)
- Opt-in observability stack as a Docker Compose profile (`--profile observability`): Grafana Loki + Grafana Alloy (scrapes container stdout) + Grafana with a pre-provisioned datasource and reliability dashboard — snark stays backend-neutral (standard JSON stdout), so any other aggregator can be used instead
- Structured `generation_event` log emitted at the reliability choke point, for log-based dashboards
- Token-authenticated Prometheus `/metrics` endpoint with a `snark_generations_total` reliability counter, plus a Prometheus service and error/fallback-rate panels in the bundled stack
- Configurable model tuning via environment: per-length token ceilings (`LENGTH_TOKENS_SHORT`/`_MEDIUM`/`_LONG`) and a global `PERSONA_MAX_TOKENS_FLOOR`
- AI provider config file (`config/providers.yaml`, overridable with `AI_PROVIDERS_FILE`) holding the default provider, fallback order, models, and endpoints; API keys stay in the environment
- Generic `openai_compatible` provider type for any OpenAI-compatible endpoint (Groq, OpenRouter, vLLM, a local Ollama), with per-provider `extra_body`
- Ollama support: a keyless `ollama` entry in the shipped providers file and a quick-start guide in the README
- Per-provider `price` and `free` settings for the dashboard cost estimate
- `host.docker.internal` is mapped to the host on both app services in `docker-compose.yml`, so containers can reach a local Ollama

### Changed

- Default Groq model is now `openai/gpt-oss-20b` (the previous default was retired by Groq)
- A provider's name is its key in `config/providers.yaml` (logs, stats, and fallback use it)
- `reasoning_effort` is now set through the provider's `extra_body`; there is no automatic retry without it when a model rejects it
- An empty reply from an `openai_compatible` provider now triggers fallback to the next provider instead of being returned
- Claude: a bad-request error is now treated as a content filter only when it mentions content filtering; the previous match on "blocked" could turn an unrelated 400 (for example an oversized prompt) into a content-filter fallback
- Startup now fails with an error when `config/providers.yaml` (or the file named by `AI_PROVIDERS_FILE`) is invalid

### Removed

- `AI_DEFAULT_PROVIDER` and `AI_PROVIDER_FALLBACK_ORDER` settings (use `default` and `fallback` in the providers file)
- `GROQ_MODEL`, `GROQ_REASONING_EFFORT`, `GEMINI_MODEL`, and `CLAUDE_MODEL` settings (use `model` and `extra_body` in the providers file)
- `PROVIDER_TOKEN_COST` setting (use `price` or `free` in the providers file)
- The `groq` dependency and dedicated Groq adapter, replaced by the `openai_compatible` provider

### Security

- `/metrics` is bearer-token authenticated and disabled unless `METRICS_AUTH_TOKEN` is set; requests without a valid token get a `404`. An application-layer IP allowlist was deliberately avoided because Docker's published-port NAT makes source IPs unreliable for access control

## [0.3.0] - 2026-07-02

### Added

- Opt-in structured JSON logging (`LOG_FORMAT=json`) plus a per-request cost/token log line, for shipping to log/metrics aggregation (Loki/Grafana)
- Configurable data-retention windows and PII-redaction controls for stored request data

### Changed

- Privacy-forward defaults: request logs auto-expire (30 days), reliability events (90 days), and user input is PII-redacted before storage — all env-overridable
- Streaming concurrency and gunicorn worker/thread counts are now configurable via environment variables

### Fixed

- Streaming can no longer exhaust the worker pool — concurrent SSE streams are bounded per worker (excess requests get a fast 503)

## [0.2.0] - 2026-07-01

### Added

- Opt-in admin panel with an interactive analytics dashboard — usage, cost, latency, and reliability metrics, persona management, and response-log browsing with retention pruning
- Accurate per-model cost estimation with an input/output token split, priced from a vendored, refreshable LiteLLM cost map (with a configurable override)
- Reliability tracking — error rate, provider-fallback frequency, and content-filter rate, with recent-failure detail
- Token usage now recorded for streamed responses

### Fixed

- Streaming reliability, and OpenAPI/Swagger accuracy for the streaming transport

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

[0.3.0]: https://github.com/PramodTKodag/snark/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/PramodTKodag/snark/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/PramodTKodag/snark/releases/tag/v0.1.0
