"""Minimal GitHub public-profile fetcher for the roast-github endpoint.

Uses only the Python standard library (urllib), so no new dependency is added.
It hits the unauthenticated GitHub REST API, which is rate-limited to 60
requests/hour per IP — fine for a low-traffic humor endpoint, and any failure
degrades cleanly to a 503 at the view layer.
"""

import json
import urllib.error
import urllib.request

GITHUB_API = "https://api.github.com/users/{username}"
_TIMEOUT = 5


class GitHubError(Exception):
    """GitHub could not be reached or returned an unexpected error."""


class GitHubUserNotFoundError(GitHubError):
    """The requested GitHub username does not exist."""


def fetch_profile(username: str) -> dict:
    """Fetch a public GitHub profile. Raises GitHubError on any failure."""
    req = urllib.request.Request(
        GITHUB_API.format(username=username),
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "snark-api",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise GitHubUserNotFoundError(username) from exc
        raise GitHubError(f"GitHub returned HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise GitHubError(str(exc)) from exc


def build_roast_context(profile: dict) -> str:
    """Turn a GitHub profile payload into a compact roast prompt."""
    parts = [f"GitHub user @{profile.get('login', 'unknown')}"]
    if profile.get("name"):
        parts.append(f"name: {profile['name']}")
    if profile.get("bio"):
        parts.append(f"bio: {profile['bio']}")
    parts.append(f"public repos: {profile.get('public_repos', 0)}")
    parts.append(f"followers: {profile.get('followers', 0)}")
    parts.append(f"following: {profile.get('following', 0)}")
    if profile.get("public_gists") is not None:
        parts.append(f"public gists: {profile['public_gists']}")
    if profile.get("created_at"):
        parts.append(f"joined: {profile['created_at'][:10]}")
    if profile.get("location"):
        parts.append(f"location: {profile['location']}")
    return (
        "Roast this developer based on their GitHub profile. Be playful and "
        "clever about their actual stats. Details — " + ", ".join(parts) + "."
    )
