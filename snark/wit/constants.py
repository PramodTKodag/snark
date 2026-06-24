# Allowed mood overrides accepted by wit endpoints.
ALLOWED_MOODS = frozenset(
    {
        "sarcastic",
        "angry",
        "funny",
        "sad",
        "excited",
        "dramatic",
        "passive-aggressive",
        "philosophical",
        "wholesome",
        "unhinged",
        "dry",
        "chaotic",
        "chill",
        "spicy",
        "deadpan",
    }
)

# Optional `length` query param. Maps to a max_tokens ceiling and a prompt hint;
# when omitted, each persona's own max_tokens is used unchanged.
ALLOWED_LENGTHS = frozenset({"short", "medium", "long"})

LENGTH_MAX_TOKENS = {
    "short": 60,
    "medium": 150,
    "long": 320,
}

# Upper bound on the free-text `lang` query param to keep prompts bounded.
MAX_LANG_LENGTH = 30
