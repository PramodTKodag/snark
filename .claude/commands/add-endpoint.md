Add a new wit endpoint to the snark API. The user will describe what the endpoint should do.

Follow the existing pattern exactly:

1. **Persona** — Add a new entry in `snark/wit/management/commands/seed_personas.py` with:
   - `slug`: URL-friendly name (used in the endpoint path)
   - `name`: Human-readable name
   - `system_prompt`: The AI persona instruction
   - `rules`: List of rules the AI must follow
   - `tone`: The mood/style
   - `temperature`: 0.7-1.0 (higher = more creative)
   - `max_tokens`: Response length limit (typically 150-300)

2. **Docs** — Add a description constant in `snark/wit/docs.py` following the existing format with summary, parameters, and example response.

3. **View** — Add a new view class in `snark/wit/views.py`:
   - Extend `APIView`
   - Use `AnonRateThrottle`
   - Call `WitService.generate(slug, user_input, ip)` — NEVER call AI providers directly
   - Return the response via `WitResponseSerializer`
   - Add `@extend_schema` decorator using the docs constant

4. **URL** — Register the new path in `snark/wit/urls.py`

5. **Tests** — Add tests in the appropriate test file under `snark/wit/tests/`

6. Run `make lint` and `make test` to verify everything works.

IMPORTANT: All AI calls MUST go through the provider abstraction via `WitService`. Never import or call AI SDKs directly in views.
