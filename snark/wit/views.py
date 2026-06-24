import json
import logging
import re

from django.http import StreamingHttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .constants import ALLOWED_MOODS
from .docs import (
    BATCH_DESC,
    BUG_BLAME_DESC,
    CODE_REVIEW_DESC,
    COMMIT_MESSAGE_DESC,
    COMPLIMENT_DESC,
    CORPORATE_JARGON_DESC,
    DEBUG_STORY_DESC,
    EXPLAIN_LIKE_IM_5_DESC,
    FORTUNE_COOKIE_DESC,
    HONEST_CHANGELOG_DESC,
    HOROSCOPE_DESC,
    HOT_TAKE_DESC,
    INCIDENT_POSTMORTEM_DESC,
    INTERVIEW_QUESTION_DESC,
    JARGON_TRANSLATOR_DESC,
    MEETING_EXCUSE_DESC,
    MOTIVATION_DESC,
    NAME_SUGGESTION_DESC,
    PERSONAS_DESC,
    PICKUP_LINE_DESC,
    PROVERB_DESC,
    RANDOM_DESC,
    RANDOM_EXCUSE_DESC,
    RATE_ANYTHING_DESC,
    REPLY_DESC,
    ROAST_DESC,
    ROAST_GITHUB_DESC,
    SAY_NO_DESC,
    SOCIAL_BIO_DESC,
    STANDUP_UPDATE_DESC,
    STATS_DESC,
    TECH_BATTLE_DESC,
    TLDR_DESC,
    WORTH_IT_DESC,
)
from .github import (
    GitHubError,
    GitHubUserNotFoundError,
    build_roast_context,
    fetch_profile,
)
from .models import Persona, ResponseLog
from .providers.base import ProviderError
from .serializers import (
    BatchRequestSerializer,
    BatchResponseSerializer,
    HealthResponseSerializer,
    PersonaListItemSerializer,
    ReplyRequestSerializer,
    StatsResponseSerializer,
    WitQuerySerializer,
    WitResponseSerializer,
)
from .services import PersonaNotFoundError, WitService

logger = logging.getLogger(__name__)


def _get_version():
    try:
        from __version__ import __version__

        return __version__
    except Exception:
        return "0.1.0"


class WitAnonThrottle(AnonRateThrottle):
    rate = "50/hour"


class EventStreamRenderer(BaseRenderer):
    """Advertises text/event-stream so DRF content negotiation accepts SSE
    clients (which send ``Accept: text/event-stream``). The streaming view
    returns a ``StreamingHttpResponse`` directly, so this renderer's ``render``
    is never actually invoked — it exists purely to satisfy negotiation."""

    media_type = "text/event-stream"
    format = "event-stream"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class BaseWitView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [WitAnonThrottle]
    renderer_classes = [JSONRenderer, EventStreamRenderer]

    def handle_generate(self, request, slug, user_input=None):
        params = WitQuerySerializer(data=request.query_params)
        if not params.is_valid():
            return Response(
                {
                    "error": "Invalid query parameters",
                    "code": "invalid_request",
                    "details": params.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        query = params.validated_data.get("q", "")
        mood = params.validated_data.get("mood") or None
        length = params.validated_data.get("length") or None
        lang = params.validated_data.get("lang") or None
        effective_input = user_input if user_input is not None else query

        if params.validated_data.get("stream"):
            return self._stream_response(slug, effective_input, mood, length, lang)

        try:
            result = WitService.generate(
                slug=slug,
                user_input=effective_input,
                mood=mood,
                length=length,
                lang=lang,
            )
            return Response(result, status=status.HTTP_200_OK)
        except PersonaNotFoundError:
            return Response(
                {"error": f"Persona '{slug}' not found", "code": "persona_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ProviderError as exc:
            logger.error("ProviderError for slug=%s: %s", slug, exc, exc_info=True)
            return Response(
                {
                    "error": "AI service temporarily unavailable",
                    "code": "provider_unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("Unexpected error for slug=%s: %s", slug, exc)
            return Response(
                {"error": "Internal server error", "code": "internal_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _stream_response(self, slug, user_input, mood, length, lang):
        response = StreamingHttpResponse(
            self._sse_events(slug, user_input, mood, length, lang),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache"
        # Tell reverse proxies (nginx) not to buffer the stream.
        response["X-Accel-Buffering"] = "no"
        return response

    @staticmethod
    def _sse_events(slug, user_input, mood, length, lang):
        try:
            for event in WitService.generate_stream(
                slug=slug,
                user_input=user_input,
                mood=mood,
                length=length,
                lang=lang,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except PersonaNotFoundError:
            err = {"error": f"Persona '{slug}' not found", "code": "persona_not_found"}
            yield f"data: {json.dumps(err)}\n\n"
        except ProviderError:
            err = {
                "error": "AI service temporarily unavailable",
                "code": "provider_unavailable",
            }
            yield f"data: {json.dumps(err)}\n\n"
        except Exception:
            logger.exception("Unexpected streaming error for slug=%s", slug)
            err = {"error": "Internal server error", "code": "internal_error"}
            yield f"data: {json.dumps(err)}\n\n"
        yield "data: [DONE]\n\n"


# ---------------------------------------------------------------------------
# Shared OpenAPI parameters
# ---------------------------------------------------------------------------

_Q_PARAM = OpenApiParameter(
    "q",
    str,
    OpenApiParameter.QUERY,
    required=False,
    description="Optional context for a personalized response",
)
_MOOD_PARAM = OpenApiParameter(
    "mood",
    str,
    OpenApiParameter.QUERY,
    required=False,
    description="Response mood. One of: " + ", ".join(sorted(ALLOWED_MOODS)),
)
_LENGTH_PARAM = OpenApiParameter(
    "length",
    str,
    OpenApiParameter.QUERY,
    required=False,
    description="Response length preset. One of: short, medium, long.",
)
_LANG_PARAM = OpenApiParameter(
    "lang",
    str,
    OpenApiParameter.QUERY,
    required=False,
    description="Language to respond in (e.g. Spanish, French). Defaults to English.",
)
_STREAM_PARAM = OpenApiParameter(
    "stream",
    bool,
    OpenApiParameter.QUERY,
    required=False,
    description=(
        "When true, stream the response token-by-token as Server-Sent Events "
        "(text/event-stream) instead of a single JSON object."
    ),
)


# ---------------------------------------------------------------------------
# Core Wit Endpoints
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["Wit"],
    summary="Creative excuse to say no",
    description=SAY_NO_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class SayNoView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "say-no")


@extend_schema(
    tags=["Wit"],
    summary="Random excuse generator",
    description=RANDOM_EXCUSE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class RandomExcuseView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "random-excuse")


@extend_schema(
    tags=["Wit"],
    summary="Corporate jargon generator",
    description=CORPORATE_JARGON_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class CorporateJargonView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "corporate-jargon")


@extend_schema(
    tags=["Wit"],
    summary="Honest git commit message",
    description=COMMIT_MESSAGE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class CommitMessageView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "commit-message")


@extend_schema(
    tags=["Wit"],
    summary="Spicy hot take on anything",
    description=HOT_TAKE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class HotTakeView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "hot-take")


@extend_schema(
    tags=["Wit"],
    summary="Wholesome compliment",
    description=COMPLIMENT_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class ComplimentView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "compliment")


@extend_schema(
    tags=["Wit"],
    summary="Who to blame when things go wrong",
    description=BUG_BLAME_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class BugBlameView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "bug-blame")


@extend_schema(
    tags=["Wit"],
    summary="Personalized roast",
    description=ROAST_DESC,
    parameters=[
        OpenApiParameter("name", str, OpenApiParameter.PATH),
        _Q_PARAM,
        _MOOD_PARAM,
        _LENGTH_PARAM,
        _LANG_PARAM,
        _STREAM_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class RoastView(BaseWitView):
    def get(self, request, name):
        sanitized = re.sub(r"[^a-zA-Z0-9 ]", "", name)[:100].strip()
        if not sanitized:
            return Response(
                {
                    "error": "Name must contain at least one alphanumeric character",
                    "code": "invalid_request",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "roast", user_input=sanitized)


@extend_schema(
    tags=["Wit"],
    summary="Is it worth it? Decision oracle",
    description=WORTH_IT_DESC,
    parameters=[
        OpenApiParameter(
            "q",
            str,
            OpenApiParameter.QUERY,
            required=True,
            description="What to evaluate",
        ),
        _MOOD_PARAM,
        _LENGTH_PARAM,
        _LANG_PARAM,
        _STREAM_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class WorthItView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required", "code": "invalid_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "worth-it", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Explain like I'm 5",
    description=EXPLAIN_LIKE_IM_5_DESC,
    parameters=[
        OpenApiParameter(
            "q",
            str,
            OpenApiParameter.QUERY,
            required=True,
            description="Topic to explain",
        ),
        _MOOD_PARAM,
        _LENGTH_PARAM,
        _LANG_PARAM,
        _STREAM_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class ExplainLikeIm5View(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required", "code": "invalid_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "explain-like-im-5", user_input=q)


# ---------------------------------------------------------------------------
# Viral & Workplace Humor Endpoints
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["Wit"],
    summary="Clever themed pickup lines",
    description=PICKUP_LINE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class PickupLineView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "pickup-line")


@extend_schema(
    tags=["Wit"],
    summary="Social media bio generator",
    description=SOCIAL_BIO_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class SocialBioView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "social-bio")


@extend_schema(
    tags=["Wit"],
    summary="Absurd motivational quote",
    description=MOTIVATION_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class MotivationView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "motivation")


@extend_schema(
    tags=["Wit"],
    summary="Fortune cookie wisdom",
    description=FORTUNE_COOKIE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class FortuneCookieView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "fortune-cookie")


@extend_schema(
    tags=["Wit"],
    summary="Absurd name suggestions for anything",
    description=NAME_SUGGESTION_DESC,
    parameters=[
        OpenApiParameter(
            "q",
            str,
            OpenApiParameter.QUERY,
            required=True,
            description="What you need to name",
        ),
        _MOOD_PARAM,
        _LENGTH_PARAM,
        _LANG_PARAM,
        _STREAM_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class NameSuggestionView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required", "code": "invalid_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "name-suggestion", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Brutally honest status update",
    description=STANDUP_UPDATE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class StandupUpdateView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "standup-update")


@extend_schema(
    tags=["Wit"],
    summary="Passive-aggressive peer feedback",
    description=CODE_REVIEW_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class CodeReviewView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "code-review")


@extend_schema(
    tags=["Wit"],
    summary="Meeting excuse or fake agenda",
    description=MEETING_EXCUSE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class MeetingExcuseView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "meeting-excuse")


@extend_schema(
    tags=["Wit"],
    summary="Insider vs outsider jargon translator",
    description=JARGON_TRANSLATOR_DESC,
    parameters=[
        OpenApiParameter(
            "q",
            str,
            OpenApiParameter.QUERY,
            required=True,
            description="Phrase to translate",
        ),
        _MOOD_PARAM,
        _LENGTH_PARAM,
        _LANG_PARAM,
        _STREAM_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class JargonTranslatorView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required", "code": "invalid_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "jargon-translator", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Incident post-mortem generator",
    description=INCIDENT_POSTMORTEM_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class IncidentPostmortemView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "incident-postmortem")


# ---------------------------------------------------------------------------
# New Endpoints
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["Wit"],
    summary="Battle judge — anything vs anything",
    description=TECH_BATTLE_DESC,
    parameters=[
        OpenApiParameter(
            "q",
            str,
            OpenApiParameter.QUERY,
            required=True,
            description="Matchup (e.g. 'coffee vs tea')",
        ),
        _MOOD_PARAM,
        _LENGTH_PARAM,
        _LANG_PARAM,
        _STREAM_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class TechBattleView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {
                    "error": "Query parameter 'q' is required — provide a matchup like 'coffee vs tea'",
                    "code": "invalid_request",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "tech-battle", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Rate anything 1-10",
    description=RATE_ANYTHING_DESC,
    parameters=[
        OpenApiParameter(
            "q", str, OpenApiParameter.QUERY, required=True, description="What to rate"
        ),
        _MOOD_PARAM,
        _LENGTH_PARAM,
        _LANG_PARAM,
        _STREAM_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class RateAnythingView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {
                    "error": "Query parameter 'q' is required — tell us what to rate",
                    "code": "invalid_request",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "rate-anything", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Modern horoscope",
    description=HOROSCOPE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class HoroscopeView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "horoscope")


@extend_schema(
    tags=["Wit"],
    summary="Brutally honest TL;DR",
    description=TLDR_DESC,
    parameters=[
        OpenApiParameter(
            "q",
            str,
            OpenApiParameter.QUERY,
            required=True,
            description="What to summarize",
        ),
        _MOOD_PARAM,
        _LENGTH_PARAM,
        _LANG_PARAM,
        _STREAM_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class TldrView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {
                    "error": "Query parameter 'q' is required — describe what to summarize",
                    "code": "invalid_request",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "tldr", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Absurd interview question",
    description=INTERVIEW_QUESTION_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class InterviewQuestionView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "interview-question")


@extend_schema(
    tags=["Wit"],
    summary="Honest changelog entry",
    description=HONEST_CHANGELOG_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class HonestChangelogView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "honest-changelog")


@extend_schema(
    tags=["Wit"],
    summary="Troubleshooting narrator",
    description=DEBUG_STORY_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class DebugStoryView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "debug-story")


@extend_schema(
    tags=["Wit"],
    summary="Ancient modern proverb",
    description=PROVERB_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class ProverbView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "proverb")


# ---------------------------------------------------------------------------
# Discovery & meta endpoints
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["Meta"],
    summary="List all available personas",
    description=PERSONAS_DESC,
    responses={200: PersonaListItemSerializer(many=True)},
)
class PersonaListView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def get(self, request):
        from django.core.cache import cache

        cache_key = "wit:personas:list"
        personas = cache.get(cache_key)
        if personas is None:
            personas = list(
                Persona.objects.filter(is_active=True)
                .order_by("name")
                .values("slug", "name", "tone")
            )
            cache.set(cache_key, personas, 300)
        return Response(personas)


@extend_schema(
    tags=["Wit"],
    summary="Random persona — surprise me",
    description=RANDOM_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM, _LENGTH_PARAM, _LANG_PARAM, _STREAM_PARAM],
    responses={200: WitResponseSerializer},
)
class RandomWitView(BaseWitView):
    def get(self, request):
        slug = (
            Persona.objects.filter(is_active=True)
            .order_by("?")
            .values_list("slug", flat=True)
            .first()
        )
        if not slug:
            return Response(
                {"error": "No personas available", "code": "persona_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return self.handle_generate(request, slug)


@extend_schema(
    tags=["Wit"],
    summary="Roast a GitHub profile",
    description=ROAST_GITHUB_DESC,
    parameters=[
        OpenApiParameter("username", str, OpenApiParameter.PATH),
        _MOOD_PARAM,
        _LENGTH_PARAM,
        _LANG_PARAM,
        _STREAM_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class RoastGithubView(BaseWitView):
    def get(self, request, username):
        # GitHub usernames are alphanumeric or single hyphens, max 39 chars.
        cleaned = re.sub(r"[^a-zA-Z0-9-]", "", username)[:39].strip("-")
        if not cleaned:
            return Response(
                {"error": "Invalid GitHub username", "code": "invalid_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            profile = fetch_profile(cleaned)
        except GitHubUserNotFoundError:
            return Response(
                {
                    "error": f"GitHub user '{cleaned}' not found",
                    "code": "github_user_not_found",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except GitHubError as exc:
            logger.warning("GitHub fetch failed for %s: %s", cleaned, exc)
            return Response(
                {"error": "Could not reach GitHub", "code": "github_unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return self.handle_generate(
            request, "roast", user_input=build_roast_context(profile)
        )


@extend_schema(
    tags=["Meta"],
    summary="Usage statistics",
    description=STATS_DESC,
    responses={200: StatsResponseSerializer},
)
class StatsView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def get(self, request):
        from django.core.cache import cache
        from django.db.models import Count, Sum

        cache_key = "wit:stats"
        stats = cache.get(cache_key)
        if stats is None:
            agg = ResponseLog.objects.aggregate(
                total=Count("id"), tokens=Sum("tokens_used")
            )
            top = (
                ResponseLog.objects.values("persona__slug", "persona__name")
                .annotate(count=Count("id"))
                .order_by("-count")[:10]
            )
            stats = {
                "total_responses": agg["total"] or 0,
                "total_tokens": agg["tokens"] or 0,
                "personas": [
                    {
                        "slug": row["persona__slug"],
                        "name": row["persona__name"],
                        "count": row["count"],
                    }
                    for row in top
                ],
            }
            cache.set(cache_key, stats, 60)
        return Response(stats)


@extend_schema(
    tags=["Wit"],
    summary="Sarcastic reply to a social post",
    description=REPLY_DESC,
    request=ReplyRequestSerializer,
    responses={200: WitResponseSerializer},
)
class ReplyView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [WitAnonThrottle]

    def post(self, request):
        serializer = ReplyRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "error": "Invalid reply request",
                    "code": "invalid_request",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = serializer.validated_data
        try:
            result = WitService.generate(
                slug="reply",
                user_input=data["post"],
                mood=data.get("mood") or None,
                # Default to a tweet-safe length unless the caller asks otherwise.
                length=data.get("length") or "short",
                lang=data.get("lang") or None,
            )
            return Response(result, status=status.HTTP_200_OK)
        except PersonaNotFoundError:
            logger.error("Reply persona missing — run seed_personas")
            return Response(
                {
                    "error": "Reply persona not configured",
                    "code": "persona_not_found",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ProviderError as exc:
            logger.error("Reply ProviderError: %s", exc)
            return Response(
                {
                    "error": "AI service temporarily unavailable",
                    "code": "provider_unavailable",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("Reply unexpected error: %s", exc)
            return Response(
                {"error": "Internal server error", "code": "internal_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@extend_schema(
    tags=["Wit"],
    summary="Batch — many personas in one request",
    description=BATCH_DESC,
    request=BatchRequestSerializer,
    responses={200: BatchResponseSerializer},
)
class BatchView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [WitAnonThrottle]

    def post(self, request):
        serializer = BatchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "error": "Invalid batch request",
                    "code": "invalid_request",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        for item in serializer.validated_data["requests"]:
            slug = item["persona"]
            try:
                results.append(
                    WitService.generate(
                        slug=slug,
                        user_input=item.get("q", ""),
                        mood=item.get("mood") or None,
                        length=item.get("length") or None,
                        lang=item.get("lang") or None,
                    )
                )
            except PersonaNotFoundError:
                results.append(
                    {
                        "error": f"Persona '{slug}' not found",
                        "code": "persona_not_found",
                        "persona": slug,
                    }
                )
            except ProviderError as exc:
                logger.error("Batch ProviderError for slug=%s: %s", slug, exc)
                results.append(
                    {
                        "error": "AI service temporarily unavailable",
                        "code": "provider_unavailable",
                        "persona": slug,
                    }
                )
            except Exception as exc:
                logger.exception("Batch unexpected error for slug=%s: %s", slug, exc)
                results.append(
                    {
                        "error": "Internal server error",
                        "code": "internal_error",
                        "persona": slug,
                    }
                )

        return Response({"results": results}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Health Endpoints
# ---------------------------------------------------------------------------


@extend_schema(tags=["Health"], summary="Liveness probe")
class LivenessView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def get(self, request):
        return Response({"status": "ok"})


@extend_schema(tags=["Health"], summary="Readiness probe")
class ReadinessView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def get(self, request):
        from django.db import connection

        try:
            connection.ensure_connection()
            return Response({"status": "ok"})
        except Exception:
            return Response(
                {"status": "unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


@extend_schema(
    tags=["Health"],
    summary="Full health status",
    responses={200: HealthResponseSerializer},
)
class HealthStatusView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def get(self, request):
        from django.core.cache import cache
        from django.db import connection

        components = {}

        try:
            connection.ensure_connection()
            components["database"] = "healthy"
        except Exception:
            components["database"] = "unhealthy"

        try:
            cache.set("health_check", "ok", 5)
            val = cache.get("health_check")
            components["redis"] = "healthy" if val == "ok" else "unhealthy"
        except Exception:
            components["redis"] = "unhealthy"

        all_healthy = all(v == "healthy" for v in components.values())
        return Response(
            {
                "status": "healthy" if all_healthy else "degraded",
                "timestamp": timezone.now().isoformat(),
                "service": "snark",
                "version": _get_version(),
                "components": components,
            },
            status=(
                status.HTTP_200_OK
                if all_healthy
                else status.HTTP_503_SERVICE_UNAVAILABLE
            ),
        )
