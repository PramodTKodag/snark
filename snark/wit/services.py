import hashlib
import logging

from django.core.cache import cache

from .constants import ALLOWED_LENGTHS, ALLOWED_MOODS, LENGTH_MAX_TOKENS
from .models import Persona, ResponseLog
from .providers import ProviderRegistry
from .providers.base import ContentFilterError, ProviderError

logger = logging.getLogger(__name__)

PERSONA_CACHE_TTL = 3600  # 1 hour
RESPONSE_CACHE_TTL = 300  # 5 minutes
ANTI_REPETITION_COUNT = 10


def persona_cache_key(slug: str) -> str:
    return f"persona:{slug}"


class PersonaNotFoundError(Exception):
    pass


class WitService:
    @staticmethod
    def generate(
        slug: str,
        user_input: str = "",
        mood: str | None = None,
        length: str | None = None,
        lang: str | None = None,
    ) -> dict:
        if mood and mood not in ALLOWED_MOODS:
            mood = None
        if length and length not in ALLOWED_LENGTHS:
            length = None
        lang = (lang or "").strip() or None
        persona = WitService._load_persona(slug)

        cache_key = WitService._response_cache_key(slug, user_input, mood, length, lang)
        cached = cache.get(cache_key)
        if cached:
            return {"response": cached, "persona": persona.name, "cached": True}

        system_prompt = WitService._build_prompt(persona, mood, length, lang)
        user_prompt = user_input or "Generate a response."
        max_tokens = LENGTH_MAX_TOKENS.get(length, persona.max_tokens)

        ai_response = WitService._generate_with_fallback(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=persona.temperature,
            max_tokens=max_tokens,
        )

        ResponseLog.objects.create(
            persona=persona,
            input_text=user_input,
            response_text=ai_response.text,
            tokens_used=ai_response.tokens_used,
            latency_ms=ai_response.latency_ms,
            provider_name=ai_response.provider,
            model_name=ai_response.model,
        )

        cache.set(cache_key, ai_response.text, RESPONSE_CACHE_TTL)

        return {"response": ai_response.text, "persona": persona.name, "cached": False}

    @staticmethod
    def _generate_with_fallback(
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ):
        """Try the default provider, then fall back to others on failure."""
        primary = ProviderRegistry.get()
        try:
            return primary.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except ContentFilterError:
            logger.warning(
                "Content filter on %s, retrying with softened prompt", primary.name
            )
            softened_system = (
                system_prompt
                + "\n\nIMPORTANT: Keep it light, playful, and safe for all audiences. "
                "Avoid anything offensive, mean-spirited, or inappropriate."
            )
            try:
                return primary.generate(
                    system_prompt=softened_system,
                    user_prompt=user_prompt,
                    temperature=max(temperature - 0.2, 0.3),
                    max_tokens=max_tokens,
                )
            except (ContentFilterError, ProviderError):
                logger.warning(
                    "Softened retry failed on %s, trying fallbacks", primary.name
                )
        except ProviderError:
            logger.warning("Provider %s failed, trying fallbacks", primary.name)

        for fallback in ProviderRegistry.get_fallbacks(exclude=primary.name):
            try:
                logger.info("Falling back to provider: %s", fallback.name)
                return fallback.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except (ContentFilterError, ProviderError) as exc:
                logger.warning("Fallback %s also failed: %s", fallback.name, exc)
                continue

        raise ProviderError("All AI providers failed to generate a response")

    @staticmethod
    def _load_persona(slug: str) -> Persona:
        cache_key = persona_cache_key(slug)
        persona = cache.get(cache_key)
        if persona:
            return persona
        try:
            persona = Persona.objects.get(slug=slug, is_active=True)
        except Persona.DoesNotExist:
            raise PersonaNotFoundError(f"Persona '{slug}' not found")
        cache.set(cache_key, persona, PERSONA_CACHE_TTL)
        return persona

    @staticmethod
    def _build_prompt(
        persona: Persona,
        mood: str | None = None,
        length: str | None = None,
        lang: str | None = None,
    ) -> str:
        recent = (
            ResponseLog.objects.filter(persona=persona)
            .order_by("-created_at")
            .values_list("response_text", flat=True)[:ANTI_REPETITION_COUNT]
        )
        rules_text = "\n".join(f"- {r}" for r in persona.rules) if persona.rules else ""
        rules_block = f"\n\nRules:\n{rules_text}" if rules_text else ""

        tone_descriptor = f"\n\nPERSONA TONE: {persona.tone}." if persona.tone else ""

        mood_text = ""
        if mood:
            mood_text = (
                f"\n\nMOOD OVERRIDE: Deliver your response in a {mood} tone. "
                "This takes priority over your default tone."
            )

        length_text = ""
        if length:
            length_hint = {
                "short": "Keep it very short — a single punchy line.",
                "medium": "A moderate length is fine — a few sentences.",
                "long": "Go longer and add more detail, but stay funny.",
            }[length]
            length_text = f"\n\nLENGTH: {length_hint}"

        lang_text = ""
        if lang:
            lang_text = (
                f"\n\nLANGUAGE: Write your entire response in {lang}. "
                "Do not add an English translation."
            )

        anti_rep = ""
        if recent:
            samples = list(recent)
            anti_rep = (
                "\n\nIMPORTANT: Do NOT repeat or closely paraphrase any of these "
                "recent responses. Be completely original:\n"
                + "\n".join(f'- "{s[:80]}"' for s in samples)
            )

        tone_guide = (
            "\n\nTONE: Use simple, everyday language. Short sentences. "
            "No fancy words, no jargon, no filler. Write like you're texting a friend."
        )
        return (
            f"{persona.system_prompt}{tone_descriptor}{mood_text}{length_text}"
            f"{lang_text}{tone_guide}{rules_block}{anti_rep}"
        )

    @staticmethod
    def _response_cache_key(
        slug: str,
        user_input: str,
        mood: str | None = None,
        length: str | None = None,
        lang: str | None = None,
    ) -> str:
        raw = f"{slug}:{user_input}:{mood or ''}:{length or ''}:{lang or ''}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"wit:resp:{digest}"
