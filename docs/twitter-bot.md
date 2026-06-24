# Build a sarcastic Twitter reply bot

Snark is the *wit engine* — you give it a post, it gives you a sarcastic reply.
Your bot owns the Twitter side (auth, listening for mentions, posting). This
recipe wires the two together in about 30 lines.

The key endpoint is [`POST /v1/wit/reply/`](../README.md#replying-to-posts):
it takes the text of a post and returns one short, tweet-length comeback.

```
curl -X POST "http://localhost:8100/v1/wit/reply/" \
  -H "Content-Type: application/json" \
  -d '{"post": "Just shipped a feature with zero tests. What could go wrong?"}'
```

```json
{
  "response": "Bold of you to assume \"what could go wrong\" is a question and not a prophecy.",
  "persona": "The Reply Guy",
  "cached": false
}
```

## Prerequisites

- A running Snark stack (`docker compose --profile dev up -d`), or a URL to one.
- [Twitter/X API](https://developer.twitter.com/) credentials with read + write access.
- `pip install tweepy requests`

## The bot

This polls your mentions and replies to each new one. Snark handles the wit;
`tweepy` handles Twitter.

```python
import os
import time

import requests
import tweepy

SNARK = os.environ.get("SNARK_API_URL", "http://localhost:8100")

client = tweepy.Client(
    bearer_token=os.environ["TW_BEARER"],
    consumer_key=os.environ["TW_API_KEY"],
    consumer_secret=os.environ["TW_API_SECRET"],
    access_token=os.environ["TW_ACCESS_TOKEN"],
    access_token_secret=os.environ["TW_ACCESS_SECRET"],
)

me = client.get_me().data.id


def snark_reply(post_text: str) -> str:
    """Ask Snark for a sarcastic, tweet-length reply to a post."""
    resp = requests.post(
        f"{SNARK}/v1/wit/reply/",
        json={"post": post_text},  # length defaults to tweet-safe "short"
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def run():
    since_id = None
    while True:
        mentions = client.get_users_mentions(me, since_id=since_id)
        for tweet in reversed(mentions.data or []):
            since_id = max(since_id or 0, tweet.id)
            try:
                reply = snark_reply(tweet.text)
                client.create_tweet(text=reply, in_reply_to_tweet_id=tweet.id)
                print(f"replied to {tweet.id}: {reply}")
            except Exception as exc:  # don't let one bad tweet kill the loop
                print(f"skipped {tweet.id}: {exc}")
        time.sleep(60)  # respect Twitter's rate limits


if __name__ == "__main__":
    run()
```

## Tips

- **Length:** `reply` defaults to `length=short` so replies fit in a tweet. Pass
  `"length": "medium"` for a chattier bot.
- **Tone:** add `"mood": "deadpan"` (or `spicy`, `dramatic`, ...) to steer the vibe.
- **Other languages:** add `"lang": "Spanish"` to reply in another language.
- **No repeats:** Snark remembers its last several replies and won't repeat the
  same joke, so your bot won't spam one punchline.

## Please be a good bot

Sarcastically replying to strangers can be harassment. Reply only to people who
**opt in** (e.g. mention your bot first), never to random users, and follow
[X's automation rules](https://help.x.com/en/rules-and-policies/x-automation).
The `reply` persona is tuned to mock the *content*, never the person, and to
avoid protected characteristics — keep it that way.
