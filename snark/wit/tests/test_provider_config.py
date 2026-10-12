from pathlib import Path

import pytest
from wit.providers.config import (
    ProviderConfigError,
    ProviderSpec,
    ProviderType,
    _build_extra_body,
    load_providers_config,
)

VALID_FILE = """\
default: groq
fallback: [gemini]
providers:
  groq:
    type: openai_compatible
    url: https://api.example.com/v1
    key: GROQ_API_KEY
    model: some/model
    extra_body:
      reasoning_effort: low
    price: [0.1, 0.5]
  ollama:
    type: openai_compatible
    url: http://localhost:11434/v1
    model: gemma3
    free: true
  gemini:
    type: gemini
    key: GEMINI_API_KEY
    model: gemini-2.0-flash
"""


def write_config(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "providers.yaml"
    path.write_text(text)
    return path


def test_valid_file_loads(tmp_path):
    config = load_providers_config(write_config(tmp_path, VALID_FILE))

    assert config.default == "groq"
    assert config.fallback == ("gemini",)
    assert list(config.providers) == ["groq", "ollama", "gemini"]
    groq = config.providers["groq"]
    assert groq.type is ProviderType.OPENAI_COMPATIBLE
    assert groq.model == "some/model"
    assert groq.key_env == "GROQ_API_KEY"
    assert groq.url == "https://api.example.com/v1"
    assert groq.extra_body == {"reasoning_effort": "low"}
    assert groq.price == (0.1, 0.5)
    assert groq.free is False
    ollama = config.providers["ollama"]
    assert ollama.key_env is None
    assert ollama.free is True
    assert ollama.price is None


SENTINEL_URL = "https://sentinel-host.invalid/v1?token=SENTINEL_QUERY"
SENTINEL_KEY = "sk-SENTINEL-LITERAL-SECRET"


def provider_block(**overrides) -> str:
    """One keyless openai_compatible provider as YAML, with field overrides."""
    fields = {
        "type": "openai_compatible",
        "url": "http://localhost:11434/v1",
        "model": "m",
    }
    fields.update(overrides)
    lines = [f"    {k}: {v}" for k, v in fields.items() if v is not None]
    return "providers:\n  p:\n" + "\n".join(lines) + "\n"


def load_error(tmp_path, text) -> str:
    with pytest.raises(ProviderConfigError) as excinfo:
        load_providers_config(write_config(tmp_path, text))
    return str(excinfo.value)


def single(**overrides) -> str:
    return "default: p\n" + provider_block(**overrides)


class TestYamlHardening:
    def test_missing_file(self, tmp_path):
        with pytest.raises(ProviderConfigError):
            load_providers_config(tmp_path / "absent.yaml")

    def test_bad_yaml_reports_line_only(self, tmp_path):
        message = load_error(tmp_path, "default: [unclosed\n  secret-token: x\n")
        assert "line" in message
        assert "secret-token" not in message

    @pytest.mark.parametrize("scalar", ["2001-13-45", "0x_"])
    def test_unconstructable_scalar_is_a_config_error_without_its_value(
        self, tmp_path, scalar
    ):
        message = load_error(tmp_path, single(model=scalar))
        assert "not valid YAML" in message
        assert scalar not in message
        assert "13" not in message

    def test_duplicate_top_level_key(self, tmp_path):
        assert "line" in load_error(tmp_path, single() + "default: p\n")

    def test_duplicate_nested_key(self, tmp_path):
        text = single() + "    extra_body:\n      a: 1\n      a: 2\n"
        assert "line" in load_error(tmp_path, text)

    def test_non_mapping_root(self, tmp_path):
        load_error(tmp_path, "- a\n- b\n")

    def test_unknown_top_level_key_not_echoed(self, tmp_path):
        message = load_error(tmp_path, single() + "surprise-field: 1\n")
        assert "surprise-field" not in message

    def test_python_object_tag_is_rejected(self, tmp_path):
        text = single(model="!!python/object/apply:os.getcwd []")
        load_error(tmp_path, text)

    def test_yaml_bool_is_not_coerced_to_string(self, tmp_path):
        load_error(tmp_path, single(model="yes"))


class TestProviderFields:
    def test_unknown_type(self, tmp_path):
        assert "'p'" in load_error(tmp_path, single(type="mystery"))

    def test_missing_model(self, tmp_path):
        load_error(tmp_path, single(model=None))

    def test_model_over_100_chars(self, tmp_path):
        load_error(tmp_path, single(model="m" * 101))

    def test_model_of_100_chars_is_allowed(self, tmp_path):
        load_providers_config(write_config(tmp_path, single(model="m" * 100)))

    def test_missing_url(self, tmp_path):
        load_error(tmp_path, single(url=None))

    @pytest.mark.parametrize("name", ["Upper", "1start", "has space", "a" * 51, '""'])
    def test_invalid_name_not_echoed(self, tmp_path, name):
        text = f"default: x\nproviders:\n  '{name}':\n    type: claude\n"
        assert name not in load_error(tmp_path, text)

    def test_name_with_trailing_newline_is_rejected(self, tmp_path):
        text = (
            'default: "p\\n"\nproviders:\n  "p\\n":\n'
            "    type: openai_compatible\n    url: http://localhost/v1\n    model: m\n"
        )
        load_error(tmp_path, text)

    def test_name_of_50_chars_is_allowed(self, tmp_path):
        name = "a" * 50
        text = f"default: {name}\n" + provider_block().replace("  p:", f"  {name}:")
        load_providers_config(write_config(tmp_path, text))

    def test_unsupported_field_not_echoed(self, tmp_path):
        message = load_error(tmp_path, single(sneaky_field=1))
        assert "sneaky_field" not in message

    def test_providers_must_be_non_empty(self, tmp_path):
        load_error(tmp_path, "default: p\nproviders: {}\n")


class TestKeyAndUrl:
    @pytest.mark.parametrize(
        "key", ["lower_case", "1ABC", "HAS-DASH", SENTINEL_KEY, "[A]", "true"]
    )
    def test_key_must_be_an_env_name(self, tmp_path, key):
        message = load_error(tmp_path, single(url="https://h/v1", key=key))
        assert SENTINEL_KEY not in message

    def test_key_with_trailing_newline_is_rejected(self, tmp_path):
        load_error(tmp_path, single(url="https://h/v1", key='"MY_API_KEY\\n"'))

    def test_key_over_http_rejected(self, tmp_path):
        load_error(tmp_path, single(key="MY_KEY", url="http://h/v1"))

    def test_key_over_https_allowed(self, tmp_path):
        config = load_providers_config(
            write_config(tmp_path, single(key="MY_KEY", url="https://h/v1"))
        )
        assert config.providers["p"].key_env == "MY_KEY"

    def test_keyless_http_allowed(self, tmp_path):
        load_providers_config(write_config(tmp_path, single(url="http://h:11434/v1")))

    @pytest.mark.parametrize(
        "url",
        [
            "https://user:pw@h/v1",
            "https://user@h/v1",
            "https://h/v1?token=x",
            "https://h/v1#frag",
            "https://h/v1?",
            "https://h/v1#",
            "ftp://h/v1",
            "https:///v1",
            "https://h:99999999/v1",
            "h/v1",
        ],
    )
    def test_bad_urls_rejected_without_echo(self, tmp_path, url):
        message = load_error(tmp_path, single(url=f"'{url}'"))
        assert url not in message


class TestDefaultAndFallback:
    def test_undefined_default(self, tmp_path):
        load_error(
            tmp_path,
            provider_block().replace("providers:", "default: nope\nproviders:", 1),
        )

    def test_missing_default(self, tmp_path):
        load_error(tmp_path, provider_block())

    def test_unknown_fallback(self, tmp_path):
        load_error(tmp_path, single() + "fallback: [ghost]\n")

    def test_duplicate_fallback(self, tmp_path):
        load_error(tmp_path, single() + "fallback: [p, p]\n")

    def test_fallback_must_be_a_list(self, tmp_path):
        load_error(tmp_path, single() + "fallback: p\n")

    def test_default_may_appear_in_fallback(self, tmp_path):
        config = load_providers_config(
            write_config(tmp_path, single() + "fallback: [p]\n")
        )
        assert config.fallback == ("p",)


class TestPriceAndFree:
    @pytest.mark.parametrize(
        "price",
        [
            "[.nan, 1]",
            "[1, .inf]",
            "[-1, 1]",
            "[true, 1]",
            "[1]",
            "[1, 2, 3]",
            "5",
            "['a', 1]",
            "[1" + "0" * 400 + ", 1]",
        ],
    )
    def test_bad_price(self, tmp_path, price):
        load_error(tmp_path, single(price=price))

    def test_zero_price_allowed(self, tmp_path):
        config = load_providers_config(write_config(tmp_path, single(price="[0, 0]")))
        assert config.providers["p"].price == (0.0, 0.0)

    def test_free_with_key(self, tmp_path):
        load_error(tmp_path, single(free="true", key="MY_KEY", url="https://h/v1"))

    def test_free_with_price(self, tmp_path):
        load_error(tmp_path, single(free="true", price="[1, 2]"))

    def test_free_must_be_a_bool(self, tmp_path):
        load_error(tmp_path, single(free="'yes'"))


class TestExtraBody:
    @pytest.mark.parametrize(
        "key",
        [
            "model",
            "messages",
            "stream",
            "stream_options",
            "max_tokens",
            "temperature",
            "n",
        ],
    )
    def test_reserved_keys_rejected(self, tmp_path, key):
        load_error(tmp_path, single() + f"    extra_body:\n      {key}: 1\n")

    def test_date_rejected(self, tmp_path):
        load_error(tmp_path, single() + "    extra_body:\n      when: 2020-01-01\n")

    def test_nan_rejected(self, tmp_path):
        load_error(tmp_path, single() + "    extra_body:\n      x: .nan\n")

    def test_nested_inf_rejected(self, tmp_path):
        load_error(tmp_path, single() + "    extra_body:\n      x: [1, {y: .inf}]\n")

    def test_cycle_rejected(self, tmp_path):
        load_error(tmp_path, single() + "    extra_body: &loop\n      self: *loop\n")

    def test_layered_aliases_are_rejected_promptly(self, tmp_path):
        layers = "".join(
            f"      l{i}: &a{i} [*a{i - 1}, *a{i - 1}, *a{i - 1}]\n"
            for i in range(1, 12)
        )
        text = single() + "    extra_body:\n      l0: &a0 [1]\n" + layers

        assert "not valid YAML" in load_error(tmp_path, text)

    def test_alias_is_rejected_even_when_harmless(self, tmp_path):
        load_error(tmp_path, single() + "    extra_body:\n      a: &x 1\n      b: *x\n")

    def test_deeply_nested_extra_body_is_a_config_error(self, tmp_path):
        text = single() + "    extra_body:\n      deep: " + "[" * 5000 + "]" * 5000

        assert "nested too deeply" in load_error(tmp_path, text)

    def test_list_cycle_rejected(self, tmp_path):
        load_error(tmp_path, single() + "    extra_body:\n      x: &loop [*loop]\n")

    def test_non_string_key_rejected(self, tmp_path):
        load_error(tmp_path, single() + "    extra_body:\n      1: x\n")

    def test_non_mapping_rejected(self, tmp_path):
        load_error(tmp_path, single() + "    extra_body: [a]\n")

    def test_valid_extra_body_is_loaded(self, tmp_path):
        text = single() + "    extra_body:\n      options:\n        think: false\n"
        config = load_providers_config(write_config(tmp_path, text))
        assert config.providers["p"].extra_body == {"options": {"think": False}}

    def test_extra_body_is_deep_copied_from_the_parsed_tree(self):
        raw = {"options": {"think": False}}

        built = _build_extra_body(raw, lambda field, problem: ValueError(problem))

        assert built == raw
        assert built is not raw and built["options"] is not raw["options"]

    def test_extra_body_defaults_to_empty(self, tmp_path):
        config = load_providers_config(write_config(tmp_path, single()))
        assert config.providers["p"].extra_body == {}


class TestNativeTypes:
    NATIVE = "default: g\nproviders:\n  g:\n    type: gemini\n    model: m\n    key: GEMINI_API_KEY\n"

    def test_native_type_loads(self, tmp_path):
        config = load_providers_config(write_config(tmp_path, self.NATIVE))
        assert config.providers["g"].type is ProviderType.GEMINI
        assert config.providers["g"].url is None

    @pytest.mark.parametrize("field", ["url: https://h/v1", "extra_body: {}"])
    @pytest.mark.parametrize("provider_type", ["gemini", "claude"])
    def test_native_types_reject_url_and_extra_body(
        self, tmp_path, field, provider_type
    ):
        text = self.NATIVE.replace("gemini", provider_type, 1) + f"    {field}\n"
        load_error(tmp_path, text)

    def test_claude_without_key(self, tmp_path):
        text = "default: c\nproviders:\n  c:\n    type: claude\n    model: m\n"
        load_error(tmp_path, text)


def test_sentinel_values_never_appear_in_any_error(tmp_path):
    bad_files = [
        single(url=f"'{SENTINEL_URL}'", key="MY_KEY"),
        single(url=f"'{SENTINEL_URL}'"),
        single(key=SENTINEL_KEY, url="https://h/v1"),
        single(model=f"'{SENTINEL_KEY}'", price="[1]"),
        single(type=SENTINEL_KEY),
        single() + f"    extra_body:\n      {SENTINEL_KEY}: 1\n      model: x\n",
        single()
        + f"    extra_body:\n      k: 2020-01-01\n      {SENTINEL_KEY}: [.nan]\n",
        f"{SENTINEL_KEY}: 1\n" + single(),
        f"default: {SENTINEL_KEY}\n" + provider_block(),
        single() + f"fallback: [{SENTINEL_KEY}]\n",
        f"default: p\nproviders:\n  {SENTINEL_KEY}:\n    type: claude\n",
        f"default: [{SENTINEL_KEY}\n",
    ]
    for text in bad_files:
        message = load_error(tmp_path, text)
        assert "SENTINEL" not in message
        assert "sentinel" not in message


class TestProviderSpecInvariants:
    """Rules hold for any construction path, not only the file loader."""

    @pytest.mark.parametrize("kind", [ProviderType.GEMINI, ProviderType.CLAUDE])
    def test_native_provider_requires_a_key(self, kind):
        with pytest.raises(ProviderConfigError):
            ProviderSpec(name="native", type=kind, model="m")

    def test_free_is_only_for_keyless_providers(self):
        with pytest.raises(ProviderConfigError):
            ProviderSpec(
                name="p",
                type=ProviderType.OPENAI_COMPATIBLE,
                model="m",
                url="https://llm.example.test/v1",
                key_env="P_API_KEY",
                free=True,
            )

    def test_free_and_price_are_mutually_exclusive(self):
        with pytest.raises(ProviderConfigError):
            ProviderSpec(
                name="p",
                type=ProviderType.OPENAI_COMPATIBLE,
                model="m",
                url="http://localhost:11434/v1",
                free=True,
                price=(1.0, 2.0),
            )
