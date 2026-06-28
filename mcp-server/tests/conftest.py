import pytest

from snark_mcp.client import SnarkAPIError


class FakeClient:
    """Stand-in for SnarkClient that records calls and returns canned data."""

    def __init__(self):
        self.calls = []

    def _resp(self, persona, text):
        return {"response": text, "persona": persona, "cached": False}

    async def wit(self, persona, q="", mood=None, length=None, lang=None):
        self.calls.append(("wit", persona, q, mood, length))
        return self._resp(persona, f"wit:{persona}:{q}")

    async def roast(self, name, mood=None, length=None, lang=None):
        self.calls.append(("roast", name, mood))
        return self._resp("The Friendly Roaster", f"roast of {name}")

    async def roast_github(self, username, mood=None, length=None, lang=None):
        self.calls.append(("roast_github", username, mood))
        return self._resp("The Friendly Roaster", f"github roast of {username}")

    async def worth_it(self, thing, mood=None, length=None, lang=None):
        self.calls.append(("worth_it", thing, mood))
        return self._resp("The Decision Oracle", f"VERDICT: NO ({thing})")

    async def reply(self, post, mood=None, length=None, lang=None):
        self.calls.append(("reply", post, mood))
        return self._resp("The Reply Guy", f"reply to {post}")

    async def list_personas(self):
        self.calls.append(("list_personas",))
        return [{"slug": "roast", "name": "The Friendly Roaster", "tone": "playful"}]


class ErrorClient:
    """Fake client whose every method raises SnarkAPIError."""

    async def roast(self, *a, **k):
        raise SnarkAPIError("Snark API error (503): AI service temporarily unavailable")

    async def roast_github(self, *a, **k):
        raise SnarkAPIError("Snark API error (503): AI service temporarily unavailable")


@pytest.fixture
def fake_client(monkeypatch):
    import snark_mcp.server as server

    fake = FakeClient()
    monkeypatch.setattr(server, "_client", fake)
    return fake


@pytest.fixture
def error_client(monkeypatch):
    import snark_mcp.server as server

    monkeypatch.setattr(server, "_client", ErrorClient())
