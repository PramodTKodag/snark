Hit a snark API endpoint to test it live. The user will specify which endpoint.

Use curl to call the endpoint against the running local server at `http://localhost:8100/v1/wit/`.

Examples:
- `curl -s http://localhost:8100/v1/wit/say-no/ | python -m json.tool`
- `curl -s http://localhost:8100/v1/wit/roast/Claude/ | python -m json.tool`
- `curl -s "http://localhost:8100/v1/wit/explain-like-im-5/?q=quantum+computing" | python -m json.tool`
- `curl -s "http://localhost:8100/v1/wit/worth-it/?q=buying+a+mechanical+keyboard" | python -m json.tool`

If the user provides a mood parameter, add `?mood=sarcastic` (or whichever mood).
Valid moods: sarcastic, angry, funny, sad, excited, dramatic, passive-aggressive, philosophical, wholesome, unhinged, dry, chaotic, chill, spicy, deadpan.

Report the response, latency, and whether it was cached.
