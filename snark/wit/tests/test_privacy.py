from wit import privacy


class TestRedact:
    def test_strips_email(self):
        assert privacy.redact("mail me at a.b+tag@example.co.uk now") == (
            "mail me at [email] now"
        )

    def test_strips_credit_card(self):
        # The pattern may absorb one trailing separator, so assert on the outcome.
        result = privacy.redact("card 4111111111111111 ok")
        assert "[card]" in result
        assert "4111" not in result

    def test_strips_ssn(self):
        # SSN is redacted before the broad phone pattern can claim it.
        assert privacy.redact("ssn 123-45-6789 here") == "ssn [ssn] here"

    def test_strips_phone(self):
        assert privacy.redact("call 555-123-4567 today") == "call [phone] today"

    def test_leaves_ordinary_text_untouched(self):
        text = "just a normal sentence with no identifiers"
        assert privacy.redact(text) == text


class TestStoreInput:
    def test_raw_mode_stores_verbatim(self, settings):
        settings.LOG_INPUT_MODE = "raw"
        text = "email me at a@b.com"
        assert privacy.store_input(text) == text

    def test_none_mode_stores_empty(self, settings):
        settings.LOG_INPUT_MODE = "none"
        assert privacy.store_input("email me at a@b.com") == ""

    def test_redacted_mode_scrubs_pii(self, settings):
        settings.LOG_INPUT_MODE = "redacted"
        assert privacy.store_input("email me at a@b.com") == "email me at [email]"

    def test_redacted_mode_truncates_to_max(self, settings):
        settings.LOG_INPUT_MODE = "redacted"
        result = privacy.store_input("x" * 600)
        assert len(result) == privacy.MAX_STORED_INPUT == 500

    def test_invalid_mode_falls_back_to_redacted(self, settings):
        settings.LOG_INPUT_MODE = "bogus"
        assert privacy.store_input("email me at a@b.com") == "email me at [email]"

    def test_empty_input_returns_empty(self, settings):
        settings.LOG_INPUT_MODE = "redacted"
        assert privacy.store_input("") == ""
