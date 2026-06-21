Check the health of the running snark service.

1. Hit the health endpoint: `curl -s http://localhost:8100/v1/wit/health/status/ | python -m json.tool`
2. Hit the liveness and readiness probes: `curl -s http://localhost:8100/v1/wit/health/live/` and `curl -s http://localhost:8100/v1/wit/health/ready/`
3. Check if Docker containers are running: `docker compose --profile dev ps`
4. Report the status of each component (API, database, Redis, AI providers)
