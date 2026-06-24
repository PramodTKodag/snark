"""snark — command-line client for the Snark humor API.

A thin, dependency-free HTTP client over the public REST API. Point it at a
running stack with ``--api`` or the ``SNARK_API_URL`` environment variable
(default: ``http://localhost:8100``).

Examples:
    snark hot-take "tabs vs spaces"
    snark roast Dave --mood spicy
    snark hot-take "remote work" --stream
    snark github torvalds
    snark personas
    snark stats
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_API = os.environ.get("SNARK_API_URL", "http://localhost:8100")
PREFIX = "v1/wit"


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("snark")
    except Exception:
        return "0.1.0"


def _url(base: str, path: str, params: dict | None = None) -> str:
    url = f"{base.rstrip('/')}/{PREFIX}/{path}"
    if params:
        query = {k: v for k, v in params.items() if v}
        if query:
            url += "?" + urllib.parse.urlencode(query)
    return url


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _stream(url: str) -> None:
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
    with urllib.request.urlopen(req) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue
            payload = line[len("data: ") :]
            if payload == "[DONE]":
                break
            event = json.loads(payload)
            if "delta" in event:
                sys.stdout.write(event["delta"])
                sys.stdout.flush()
            elif "error" in event:
                sys.stderr.write("\n" + event["error"] + "\n")
    print()


def _print_response(data: dict) -> None:
    print(data.get("response", ""))
    persona = data.get("persona")
    if persona:
        print(f"\n— {persona}", file=sys.stderr)


def _cmd_personas(base: str) -> None:
    for p in _get_json(_url(base, "personas/")):
        print(f"{p['slug']:<22} {p['name']}  ({p['tone']})")


def _cmd_stats(base: str) -> None:
    data = _get_json(_url(base, "stats/"))
    print(f"Total responses: {data['total_responses']:,}")
    print(f"Total tokens:    {data['total_tokens']:,}")
    if data["personas"]:
        print("Top personas:")
        for row in data["personas"]:
            print(f"  {row['count']:>6}  {row['slug']} ({row['name']})")


def run(args: argparse.Namespace) -> None:
    base = args.api
    endpoint = args.endpoint
    text = args.text or ""

    if endpoint == "personas":
        return _cmd_personas(base)
    if endpoint == "stats":
        return _cmd_stats(base)

    params = {"mood": args.mood, "length": args.length, "lang": args.lang}

    if endpoint == "roast":
        if not text:
            sys.exit("usage: snark roast <name>")
        path = f"roast/{urllib.parse.quote(text)}/"
    elif endpoint == "github":
        if not text:
            sys.exit("usage: snark github <username>")
        path = f"roast-github/{urllib.parse.quote(text)}/"
    elif endpoint == "random":
        path = "random/"
        params["q"] = text
    else:
        # Any other value is treated as a persona slug (hot-take, proverb, ...).
        path = f"{endpoint}/"
        params["q"] = text

    if args.stream:
        _stream(_url(base, path, {**params, "stream": "true"}))
    else:
        _print_response(_get_json(_url(base, path, params)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="snark",
        description="Command-line client for the Snark humor API.",
        epilog=(
            "examples:\n"
            '  snark hot-take "tabs vs spaces"\n'
            "  snark roast Dave --mood spicy\n"
            '  snark hot-take "remote work" --stream\n'
            "  snark github torvalds\n"
            "  snark personas\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "endpoint",
        help=(
            "persona slug (e.g. hot-take, commit-message), or one of: "
            "personas, stats, random, roast <name>, github <username>"
        ),
    )
    parser.add_argument(
        "text", nargs="?", default="", help="context, name, or username"
    )
    parser.add_argument("--mood", help="response mood (e.g. spicy, dramatic)")
    parser.add_argument(
        "--length", choices=["short", "medium", "long"], help="response length"
    )
    parser.add_argument("--lang", help="language to respond in")
    parser.add_argument(
        "--stream", action="store_true", help="stream tokens as they arrive"
    )
    parser.add_argument(
        "--api",
        default=DEFAULT_API,
        help=f"API base URL (default: {DEFAULT_API}, or $SNARK_API_URL)",
    )
    parser.add_argument("--version", action="version", version=f"snark {_version()}")
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    try:
        run(args)
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            msg = body.get("error", str(exc))
        except Exception:
            msg = str(exc)
        sys.exit(f"error ({exc.code}): {msg}")
    except urllib.error.URLError as exc:
        sys.exit(
            f"error: could not reach {args.api} ({exc.reason}). " "Is the API running?"
        )
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
