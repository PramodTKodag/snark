from unittest.mock import patch

import cli


def _args(*argv):
    return cli.build_parser().parse_args(list(argv))


def test_url_drops_empty_params():
    url = cli._url(
        "http://h:8100/", "hot-take/", {"q": "pizza", "mood": "", "lang": ""}
    )
    assert url.startswith("http://h:8100/v1/wit/hot-take/?")
    assert "q=pizza" in url
    assert "mood" not in url and "lang" not in url


def test_generic_slug_uses_query(capsys):
    with patch.object(
        cli,
        "_get_json",
        return_value={"response": "yo", "persona": "P", "cached": False},
    ) as g:
        cli.run(_args("hot-take", "pizza"))
    url = g.call_args.args[0]
    assert "/v1/wit/hot-take/?" in url
    assert "q=pizza" in url
    assert "yo" in capsys.readouterr().out


def test_roast_uses_path():
    with patch.object(
        cli,
        "_get_json",
        return_value={"response": "r", "persona": "P", "cached": False},
    ) as g:
        cli.run(_args("roast", "Dave"))
    assert "/v1/wit/roast/Dave/" in g.call_args.args[0]


def test_github_uses_path():
    with patch.object(
        cli,
        "_get_json",
        return_value={"response": "r", "persona": "P", "cached": False},
    ) as g:
        cli.run(_args("github", "torvalds"))
    assert "/v1/wit/roast-github/torvalds/" in g.call_args.args[0]


def test_personas_lists(capsys):
    rows = [{"slug": "roast", "name": "The Friendly Roaster", "tone": "playful"}]
    with patch.object(cli, "_get_json", return_value=rows):
        cli.run(_args("personas"))
    assert "roast" in capsys.readouterr().out


def test_stream_flag_hits_stream_endpoint():
    with patch.object(cli, "_stream") as s:
        cli.run(_args("hot-take", "pizza", "--stream"))
    url = s.call_args.args[0]
    assert "stream=true" in url
    assert "/v1/wit/hot-take/" in url


def test_api_override_changes_base():
    with patch.object(
        cli,
        "_get_json",
        return_value={"response": "x", "persona": "P", "cached": False},
    ) as g:
        cli.run(_args("hot-take", "hi", "--api", "http://example.com:9000"))
    assert g.call_args.args[0].startswith("http://example.com:9000/v1/wit/")
