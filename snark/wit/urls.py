from django.urls import path

from .views import (
    BugBlameView,
    CodeReviewView,
    CommitMessageView,
    ComplimentView,
    CorporateJargonView,
    DebugStoryView,
    ExplainLikeIm5View,
    FortuneCookieView,
    HonestChangelogView,
    HoroscopeView,
    HotTakeView,
    IncidentPostmortemView,
    InterviewQuestionView,
    JargonTranslatorView,
    MeetingExcuseView,
    MotivationView,
    NameSuggestionView,
    PickupLineView,
    ProverbView,
    RandomExcuseView,
    RateAnythingView,
    RoastView,
    SayNoView,
    SocialBioView,
    StandupUpdateView,
    TechBattleView,
    TldrView,
    WorthItView,
)

urlpatterns = [
    # Core wit endpoints
    path("say-no/", SayNoView.as_view(), name="wit-say-no"),
    path("random-excuse/", RandomExcuseView.as_view(), name="wit-random-excuse"),
    path(
        "corporate-jargon/", CorporateJargonView.as_view(), name="wit-corporate-jargon"
    ),
    path("commit-message/", CommitMessageView.as_view(), name="wit-commit-message"),
    path("hot-take/", HotTakeView.as_view(), name="wit-hot-take"),
    path("compliment/", ComplimentView.as_view(), name="wit-compliment"),
    path("bug-blame/", BugBlameView.as_view(), name="wit-bug-blame"),
    path("roast/<str:name>/", RoastView.as_view(), name="wit-roast"),
    path("worth-it/", WorthItView.as_view(), name="wit-worth-it"),
    path(
        "explain-like-im-5/", ExplainLikeIm5View.as_view(), name="wit-explain-like-im-5"
    ),
    # Viral & workplace humor
    path("pickup-line/", PickupLineView.as_view(), name="wit-pickup-line"),
    path("social-bio/", SocialBioView.as_view(), name="wit-social-bio"),
    path("motivation/", MotivationView.as_view(), name="wit-motivation"),
    path("fortune-cookie/", FortuneCookieView.as_view(), name="wit-fortune-cookie"),
    path("name-suggestion/", NameSuggestionView.as_view(), name="wit-name-suggestion"),
    path("standup-update/", StandupUpdateView.as_view(), name="wit-standup-update"),
    path("code-review/", CodeReviewView.as_view(), name="wit-code-review"),
    path("meeting-excuse/", MeetingExcuseView.as_view(), name="wit-meeting-excuse"),
    path(
        "jargon-translator/",
        JargonTranslatorView.as_view(),
        name="wit-jargon-translator",
    ),
    path(
        "incident-postmortem/",
        IncidentPostmortemView.as_view(),
        name="wit-incident-postmortem",
    ),
    # New endpoints
    path("tech-battle/", TechBattleView.as_view(), name="wit-tech-battle"),
    path("rate-anything/", RateAnythingView.as_view(), name="wit-rate-anything"),
    path("horoscope/", HoroscopeView.as_view(), name="wit-horoscope"),
    path("tldr/", TldrView.as_view(), name="wit-tldr"),
    path(
        "interview-question/",
        InterviewQuestionView.as_view(),
        name="wit-interview-question",
    ),
    path(
        "honest-changelog/", HonestChangelogView.as_view(), name="wit-honest-changelog"
    ),
    path("debug-story/", DebugStoryView.as_view(), name="wit-debug-story"),
    path("proverb/", ProverbView.as_view(), name="wit-proverb"),
]
