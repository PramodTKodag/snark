Start the snark development environment.

1. Check if `.env` exists, if not copy from `.env.example` and warn the user to add API keys
2. Run `docker compose --profile dev up --build`
3. After startup, verify the health endpoint at `http://localhost:8100/v1/wit/health/status/`

If the user says "down" or "stop", run `docker compose --profile dev down` instead.
