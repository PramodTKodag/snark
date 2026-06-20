import logging
import re

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .docs import (
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
    PICKUP_LINE_DESC,
    PROVERB_DESC,
    RANDOM_EXCUSE_DESC,
    RATE_ANYTHING_DESC,
    ROAST_DESC,
    SAY_NO_DESC,
    SOCIAL_BIO_DESC,
    STANDUP_UPDATE_DESC,
    TECH_BATTLE_DESC,
    TLDR_DESC,
    WORTH_IT_DESC,
)
from .providers.base import ProviderError
from .serializers import HealthResponseSerializer, WitQuerySerializer, WitResponseSerializer

logger = logging.getLogger(__name__)
from .services import PersonaNotFoundError, WitService


def _get_version():
    try:
        from __version__ import __version__

        return __version__
    except Exception:
        return "0.1.0"


class WitAnonThrottle(AnonRateThrottle):
    rate = "50/hour"


class BaseWitView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [WitAnonThrottle]

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
        effective_input = user_input if user_input is not None else query

        try:
            result = WitService.generate(slug=slug, user_input=effective_input, mood=mood)
            return Response(result, status=status.HTTP_200_OK)
        except PersonaNotFoundError:
            return Response(
                {"error": f"Persona '{slug}' not found", "code": "persona_not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ProviderError as exc:
            logger.error("ProviderError for slug=%s: %s", slug, exc, exc_info=True)
            return Response(
                {"error": "AI service temporarily unavailable", "code": "provider_unavailable"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("Unexpected error for slug=%s: %s", slug, exc)
            return Response(
                {"error": "Internal server error", "code": "internal_error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ---------------------------------------------------------------------------
# Shared OpenAPI parameters
# ---------------------------------------------------------------------------

_Q_PARAM = OpenApiParameter("q", str, OpenApiParameter.QUERY, required=False, description="Optional context for a personalized response")
_MOOD_PARAM = OpenApiParameter("mood", str, OpenApiParameter.QUERY, required=False, description="Response mood (e.g. sarcastic, angry, funny, sad, excited, dramatic, passive-aggressive, philosophical, wholesome, unhinged)")


# ---------------------------------------------------------------------------
# Core Wit Endpoints
# ---------------------------------------------------------------------------


@extend_schema(
    tags=["Wit"],
    summary="Creative excuse to say no",
    description=SAY_NO_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class SayNoView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "say-no")


@extend_schema(
    tags=["Wit"],
    summary="Random excuse generator",
    description=RANDOM_EXCUSE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class RandomExcuseView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "random-excuse")


@extend_schema(
    tags=["Wit"],
    summary="Corporate jargon generator",
    description=CORPORATE_JARGON_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class CorporateJargonView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "corporate-jargon")


@extend_schema(
    tags=["Wit"],
    summary="Honest git commit message",
    description=COMMIT_MESSAGE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class CommitMessageView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "commit-message")


@extend_schema(
    tags=["Wit"],
    summary="Spicy hot take on anything",
    description=HOT_TAKE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class HotTakeView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "hot-take")


@extend_schema(
    tags=["Wit"],
    summary="Wholesome compliment",
    description=COMPLIMENT_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class ComplimentView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "compliment")


@extend_schema(
    tags=["Wit"],
    summary="Who to blame when things go wrong",
    description=BUG_BLAME_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
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
    ],
    responses={200: WitResponseSerializer},
)
class RoastView(BaseWitView):
    def get(self, request, name):
        sanitized = re.sub(r"[^a-zA-Z0-9 ]", "", name)[:100].strip()
        if not sanitized:
            return Response(
                {"error": "Name must contain at least one alphanumeric character"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "roast", user_input=sanitized)


@extend_schema(
    tags=["Wit"],
    summary="Is it worth it? Decision oracle",
    description=WORTH_IT_DESC,
    parameters=[OpenApiParameter("q", str, OpenApiParameter.QUERY, required=True, description="What to evaluate"), _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class WorthItView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "worth-it", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Explain like I'm 5",
    description=EXPLAIN_LIKE_IM_5_DESC,
    parameters=[OpenApiParameter("q", str, OpenApiParameter.QUERY, required=True, description="Topic to explain"), _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class ExplainLikeIm5View(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required"},
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
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class PickupLineView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "pickup-line")


@extend_schema(
    tags=["Wit"],
    summary="Social media bio generator",
    description=SOCIAL_BIO_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class SocialBioView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "social-bio")


@extend_schema(
    tags=["Wit"],
    summary="Absurd motivational quote",
    description=MOTIVATION_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class MotivationView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "motivation")


@extend_schema(
    tags=["Wit"],
    summary="Fortune cookie wisdom",
    description=FORTUNE_COOKIE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
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
        OpenApiParameter("q", str, OpenApiParameter.QUERY, required=True, description="What you need to name"),
        _MOOD_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class NameSuggestionView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "name-suggestion", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Brutally honest status update",
    description=STANDUP_UPDATE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class StandupUpdateView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "standup-update")


@extend_schema(
    tags=["Wit"],
    summary="Passive-aggressive peer feedback",
    description=CODE_REVIEW_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class CodeReviewView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "code-review")


@extend_schema(
    tags=["Wit"],
    summary="Meeting excuse or fake agenda",
    description=MEETING_EXCUSE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
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
        OpenApiParameter("q", str, OpenApiParameter.QUERY, required=True, description="Phrase to translate"),
        _MOOD_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class JargonTranslatorView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "jargon-translator", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Incident post-mortem generator",
    description=INCIDENT_POSTMORTEM_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
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
        OpenApiParameter("q", str, OpenApiParameter.QUERY, required=True, description="Matchup (e.g. 'coffee vs tea')"),
        _MOOD_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class TechBattleView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required — provide a matchup like 'coffee vs tea'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "tech-battle", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Rate anything 1-10",
    description=RATE_ANYTHING_DESC,
    parameters=[
        OpenApiParameter("q", str, OpenApiParameter.QUERY, required=True, description="What to rate"),
        _MOOD_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class RateAnythingView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required — tell us what to rate"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "rate-anything", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Modern horoscope",
    description=HOROSCOPE_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
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
        OpenApiParameter("q", str, OpenApiParameter.QUERY, required=True, description="What to summarize"),
        _MOOD_PARAM,
    ],
    responses={200: WitResponseSerializer},
)
class TldrView(BaseWitView):
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response(
                {"error": "Query parameter 'q' is required — describe what to summarize"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return self.handle_generate(request, "tldr", user_input=q)


@extend_schema(
    tags=["Wit"],
    summary="Absurd interview question",
    description=INTERVIEW_QUESTION_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class InterviewQuestionView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "interview-question")


@extend_schema(
    tags=["Wit"],
    summary="Honest changelog entry",
    description=HONEST_CHANGELOG_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class HonestChangelogView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "honest-changelog")


@extend_schema(
    tags=["Wit"],
    summary="Troubleshooting narrator",
    description=DEBUG_STORY_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class DebugStoryView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "debug-story")


@extend_schema(
    tags=["Wit"],
    summary="Ancient modern proverb",
    description=PROVERB_DESC,
    parameters=[_Q_PARAM, _MOOD_PARAM],
    responses={200: WitResponseSerializer},
)
class ProverbView(BaseWitView):
    def get(self, request):
        return self.handle_generate(request, "proverb")


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
            status=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
