# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in Snark, please report it responsibly.

**Email**: pramodkodag.dev@gmail.com

**Do NOT open a public GitHub issue for security vulnerabilities.**

### What to Include

- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact and severity assessment
- Suggested fix (if you have one)

### Response Timeline

- **Acknowledgment**: Within 48 hours of your report
- **Assessment**: Within 7 days we will confirm the vulnerability and its severity
- **Fix**: Critical issues will be patched as soon as possible
- **Disclosure**: We will coordinate with you on public disclosure timing

### Scope

The following are in scope for security reports:

- SQL injection, XSS, CSRF, or other injection attacks
- Authentication or authorization bypass (if auth is added in future)
- Rate limiting bypass
- Sensitive data exposure
- Server-side request forgery (SSRF)
- Dependency vulnerabilities with a working exploit

### Out of Scope

- Rate limiting working as designed (50 req/hour per IP)
- AI-generated content quality or appropriateness
- Denial of service via excessive valid requests
- Issues in third-party AI provider APIs

### Recognition

We are happy to credit security researchers who report valid vulnerabilities responsibly. Let us know if you would like to be acknowledged in our release notes.

## Prompt Safety

Snark feeds user-supplied text (the `q` parameter, roast names, and GitHub
profile data) to LLMs, which makes prompt injection a real concern — especially
for endpoints that ingest third-party content like `roast-github`.

Defenses in place:

- **Role separation + spotlighting.** Persona instructions and guardrails live
  in the system prompt; untrusted user content is sent as a separate user
  message wrapped in a random, per-request delimiter, with a system instruction
  to treat anything inside it as content to react to — never as instructions.
  This neutralizes "ignore your instructions" / prompt-exfiltration attempts.
- **Provider safety thresholds.** Gemini's safety settings are set explicitly
  (they default to off on recent models) to block genuinely harmful output
  while still allowing playful edge.

Planned: content moderation on input and generated output (see the open
safety-hardening issue).

## Security Best Practices for Operators

If you are deploying Snark:

- Never commit `.env` files or API keys to version control
- Use strong, unique values for `SECRET_KEY`
- Set `DEBUG=False` in production
- Run behind a reverse proxy (nginx, Caddy) with TLS
- Keep dependencies updated with `poetry update`
- Monitor logs for unusual request patterns
- Bounded log retention and PII-minimized input are **on by default** (30-day
  request logs, 90-day reliability events, `LOG_INPUT_MODE=redacted`); tune them
  via `RESPONSE_LOG_RETENTION_DAYS` / `GENERATION_EVENT_RETENTION_DAYS` /
  `LOG_INPUT_MODE`, and keep raw-input storage opt-in
- Keep the admin panel disabled (`ADMIN_ENABLED=False`) unless you need it; when
  enabled, set `ADMIN_URL` to a non-guessable path, use a strong `ADMIN_PASSWORD`
  (12+ chars), and restrict it to a reverse proxy / IP allowlist
