Add a new AI provider to the snark provider abstraction layer.

Follow the existing pattern in `snark/wit/providers/`:

1. **Provider class** — Create `snark/wit/providers/{name}_provider.py`:
   - Import and extend `AIProvider` from `.base`
   - Implement `generate(system_prompt, user_prompt, temperature, max_tokens) -> dict`
   - Return `{"text": str, "tokens_used": int, "model": str, "provider": str}`
   - Raise `ContentFilterError` for content filter blocks
   - Raise `ProviderError` for all other failures
   - Load the API key from environment using `decouple.config()`

2. **Registry** — Register the provider in `snark/wit/providers/registry.py`

3. **Init** — Export from `snark/wit/providers/__init__.py`

4. **Seed command** — Add to `snark/wit/management/commands/seed_providers.py`

5. **Environment** — Add the API key variable to `.env.example`

6. **Tests** — Add provider tests in `snark/wit/tests/test_providers.py`

7. Run `make lint` and `make test` to verify.

Reference existing providers (groq, gemini, claude) for the exact pattern.
