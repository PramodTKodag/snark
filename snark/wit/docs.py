"""
OpenAPI descriptions for all Wit endpoints.

Kept separate from views.py so the view logic stays clean.
drf-spectacular renders markdown in descriptions.
"""

SAY_NO_DESC = (
    "Returns a uniquely AI-generated creative refusal. Perfect for when you need "
    "an elaborate excuse to decline anything — a meeting invite, a favor, "
    "a dinner party, or someone asking you to help them move.\n\n"
    "**When to use:** Need a funny way to say no? This endpoint has you covered.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/say-no/\nGET /v1/wit/say-no/?q=can you help me move this weekend\n"
    "GET /v1/wit/say-no/?q=can you cover my shift&mood=dramatic\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "I would, but I just signed a non-compete clause with my couch '
    'that specifically prohibits weekend labor.",\n'
    '  "persona": "The Refusal Artist",\n'
    '  "cached": false\n'
    "}\n```"
)

RANDOM_EXCUSE_DESC = (
    "Generates an almost-plausible excuse for any situation. These sound just credible "
    "enough to make someone pause before realizing they're absurd. Perfect for explaining "
    "why you're late, missed a deadline, or forgot something important.\n\n"
    "**When to use:** You need an excuse and the truth is too boring.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/random-excuse/\nGET /v1/wit/random-excuse/?q=late to dinner\n"
    "GET /v1/wit/random-excuse/?q=forgot your birthday&mood=deadpan\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "Sorry I\'m late — my GPS rerouted me through 1987 and I had to wait '
    'for the DeLorean to recalibrate. Traffic was surprisingly light for a paradox.",\n'
    '  "persona": "The Excuse Machine",\n'
    '  "cached": false\n'
    "}\n```"
)

CORPORATE_JARGON_DESC = (
    "Produces grammatically perfect, semantically empty corporate buzzword sentences. "
    "Ideal for filling out performance reviews, generating LinkedIn posts, or surviving "
    "your next all-hands meeting. Maximum jargon, minimum meaning.\n\n"
    "**When to use:** You need to sound important without saying anything.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/corporate-jargon/\nGET /v1/wit/corporate-jargon/?q=quarterly planning\n"
    "GET /v1/wit/corporate-jargon/?mood=excited\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "We need to leverage our cross-functional synergies to disrupt the '
    'paradigm shift in our vertical integration pipeline going forward.",\n'
    '  "persona": "The Synergy Maximizer",\n'
    '  "cached": false\n'
    "}\n```"
)

COMMIT_MESSAGE_DESC = (
    "Generates brutally honest git commit messages in conventional commit format "
    "(feat:, fix:, chore:, etc.) that reveal what actually happened. "
    "Give it non-coding context and it'll adapt the format hilariously.\n\n"
    "**When to use:** Need a laugh after your 47th `fix: stuff` commit, "
    "or want life events in commit format.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/commit-message/\nGET /v1/wit/commit-message/?q=spent 4 hours on a typo\n"
    "GET /v1/wit/commit-message/?q=tried a new recipe&mood=exhausted\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "fix: mass-replace console.log with actual error handling before PR review'
    "\\n\\n"
    'I have mass-printed more logs than a lumberjack this sprint",\n'
    '  "persona": "The Honest Committer",\n'
    '  "cached": false\n'
    "}\n```"
)

HOT_TAKE_DESC = (
    "Delivers controversial, debate-worthy opinions on any topic with 'Twitter at 2 AM' "
    "energy. Targets ideas and practices, never people. Works for tech, food, sports, "
    "music, fashion — anything.\n\n"
    "**When to use:** The group chat is too quiet and you want to start a war.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/hot-take/\nGET /v1/wit/hot-take/?q=pineapple on pizza\n"
    "GET /v1/wit/hot-take/?q=remote work&mood=unhinged\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "Pineapple on pizza isn\'t a topping choice, it\'s a personality test. '
    'And most of you are failing.",\n'
    '  "persona": "The Hot Take Machine",\n'
    '  "cached": false\n'
    "}\n```"
)

COMPLIMENT_DESC = (
    "Generates genuinely uplifting compliments tailored to any person or profession. "
    "Give it context — a chef, teacher, nurse, developer, parent — and it'll reference "
    "what makes their work meaningful. No context? You'll get a universally warm compliment.\n\n"
    "**When to use:** Someone needs a boost, or you do.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/compliment/\nGET /v1/wit/compliment/?q=just survived a double shift\n"
    "GET /v1/wit/compliment/?q=new teacher&mood=wholesome\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "The way you show up and give your best even on the days it feels '
    "invisible? That's not just dedication — that's the kind of quiet strength that "
    'makes everyone around you better.",\n'
    '  "persona": "The Wholesome Bot",\n'
    '  "cached": false\n'
    "}\n```"
)

BUG_BLAME_DESC = (
    "Determines who (or what) is truly responsible when something goes wrong. Blames "
    "inanimate objects, cosmic events, historical figures — delivered like a noir "
    "detective cracking the case. Never blames real living people. Works for any mishap.\n\n"
    "**When to use:** Something went wrong and you need a scapegoat.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/bug-blame/\nGET /v1/wit/bug-blame/?q=the souffl%C3%A9 collapsed\n"
    "GET /v1/wit/bug-blame/?q=lost my keys again&mood=dramatic\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "After a thorough investigation, I can confirm the collapse was caused '
    "by a rogue air molecule that achieved sentience during the preheat phase. It has since "
    'been apprehended. Case closed.",\n'
    '  "persona": "The Blame Allocator",\n'
    '  "cached": false\n'
    "}\n```"
)

ROAST_DESC = (
    "Creates a personalized, playful roast based on the given name. Uses name-based "
    "wordplay, rhymes, and gentle humor. Think comedy roast — clever and kind, never "
    "hurtful. The `name` path parameter is sanitized (alphanumeric only, max 100 chars).\n\n"
    "**When to use:** A friend dares you to roast them.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/roast/Alice/\nGET /v1/wit/roast/Bob/?mood=savage\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "Alice, you\'re the kind of person who color-codes their grocery list '
    "but can't remember where they parked. Your organizational skills peak exactly where "
    'they matter least.",\n'
    '  "persona": "The Friendly Roaster",\n'
    '  "cached": false\n'
    "}\n```"
)

WORTH_IT_DESC = (
    "The Decision Oracle delivers a definitive verdict on whether something is worth it. "
    "Every response starts with **VERDICT: YES** or **VERDICT: NO**, followed by an absurd "
    "but oddly compelling justification. `q` parameter is required. Works for any decision.\n\n"
    "**When to use:** You can't decide and need an authority figure (who happens to be unhinged).\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/worth-it/?q=learning to cook\n"
    "GET /v1/wit/worth-it/?q=getting a cat&mood=philosophical\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "VERDICT: YES. According to the ancient scrolls of domesticity, those '
    "who cook achieve enlightenment through 847 burnt onions. The smoke detector is merely "
    'a mirror reflecting your ambition.",\n'
    '  "persona": "The Decision Oracle",\n'
    '  "cached": false\n'
    "}\n```"
)

EXPLAIN_LIKE_IM_5_DESC = (
    "Explains any complex concept using the vocabulary and analogies a 5-year-old "
    "would understand. Cookies, playgrounds, crayons, and toy boxes are the primary "
    "teaching tools. Surprisingly accurate. `q` parameter is required.\n\n"
    "**When to use:** You need to explain something complicated to anyone (or yourself).\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/explain-like-im-5/?q=stock market\n"
    "GET /v1/wit/explain-like-im-5/?q=how wifi works&mood=excited\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "Okay so imagine you have a lemonade stand. The stock market is like '
    "a GIANT playground where grown-ups trade pieces of paper that say 'I own a tiny bit "
    "of this lemonade stand.' If everyone wants your lemonade, your paper is worth MORE "
    "cookies. If nobody wants it, your paper is worth fewer cookies. Sometimes everyone "
    "panics and trades all their papers for cookies at once. That's called a 'crash' "
    '(a big playground tantrum).",\n'
    '  "persona": "The Kindergarten Professor",\n'
    '  "cached": false\n'
    "}\n```"
)

PICKUP_LINE_DESC = (
    "Generates clever, themed pickup lines. Give it a profession, hobby, or topic and "
    "the line will be tailored — cooking, music, science, gaming, tech, anything. "
    "No context? You'll get a wildcard charmer. Kept PG-13.\n\n"
    "**When to use:** You want to make someone groan-laugh (or horrify them).\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/pickup-line/\nGET /v1/wit/pickup-line/?q=chef\n"
    "GET /v1/wit/pickup-line/?q=musician&mood=wholesome\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "Are you a five-star recipe? Because I\'ve been looking for you my '
    "whole life and I'm pretty sure you're out of my league.\",\n"
    '  "persona": "The Smooth Operator",\n'
    '  "cached": false\n'
    "}\n```"
)

SOCIAL_BIO_DESC = (
    "Crafts creative, memorable social media bios for anyone — professional enough for "
    "LinkedIn but interesting enough for Twitter/X. Pass a role, hobby, or topic via `q` "
    "to tailor the bio.\n\n"
    "**When to use:** Your current bio says 'passionate about life' and you want to fix that.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/social-bio/\nGET /v1/wit/social-bio/?q=pastry chef\n"
    "GET /v1/wit/social-bio/?q=freelance photographer&mood=dramatic\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "Turning flour into feelings since 2019. My croissants have better '
    "layers than most people's personalities. Opinions are my own; the butter is "
    "everyone's.\",\n"
    '  "persona": "The Bio Architect",\n'
    '  "cached": false\n'
    "}\n```"
)

MOTIVATION_DESC = (
    "Produces motivational quotes that start profound and end ridiculous (or vice versa). "
    "Screenshot-worthy, shareable, and genuinely uplifting underneath the humor. "
    "Give it context — cooking, fitness, parenting, coding — and it'll adapt.\n\n"
    "**When to use:** You need a boost and normal motivation is too boring.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/motivation/\nGET /v1/wit/motivation/?q=gym motivation\n"
    "GET /v1/wit/motivation/?q=imposter syndrome&mood=philosophical\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "Remember: every expert was once a beginner who almost quit on day '
    "two. You're not behind — you're loading. "
    '— Ancient Scrolls of Motivation, Chapter 12",\n'
    '  "persona": "The Absurd Motivator",\n'
    '  "cached": false\n'
    "}\n```"
)

FORTUNE_COOKIE_DESC = (
    "Delivers fortune cookie wisdom for the modern age — blending ancient mysticism "
    "with contemporary reality. Short, cryptic, oddly relevant. Give it a topic "
    "to tailor the prophecy.\n\n"
    "**When to use:** You need cosmic guidance before making a questionable decision.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/fortune-cookie/\nGET /v1/wit/fortune-cookie/?q=career change\n"
    "GET /v1/wit/fortune-cookie/?mood=mystical\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "The one who fears the unknown path has already walked it in their '
    'dreams. Lucky numbers: 7, 42, 88.",\n'
    '  "persona": "The Fortune Oracle",\n'
    '  "cached": false\n'
    "}\n```"
)

NAME_SUGGESTION_DESC = (
    "Given a description of anything that needs naming, suggests hilariously bad "
    "(but creative) options. Works for variables, projects, pets, babies, bands, "
    "businesses, Wi-Fi networks — anything. `q` parameter is required.\n\n"
    "**When to use:** You've been staring at a blank name field for 20 minutes.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/name-suggestion/?q=my new cat\n"
    "GET /v1/wit/name-suggestion/?q=our startup&mood=dramatic\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "Here are my professional naming recommendations:\\n\\n'
    "1. `Whiskers` — boring but functional\\n"
    "2. `Sir Fluffington the Third, Esquire`\\n"
    "3. `Chairman Meow`\\n"
    "4. `That Cat From The Internet`\\n"
    "5. `Greg`\\n\\n"
    'I recommend #5 for maximum confusion at the vet.",\n'
    '  "persona": "The Naming Consultant",\n'
    '  "cached": false\n'
    "}\n```"
)

STANDUP_UPDATE_DESC = (
    "Generates realistic daily status updates in the classic **Yesterday / Today / Blockers** "
    "format — but with what people *actually* did vs what they say. Works for any profession. "
    "Give it context to tailor the update.\n\n"
    "**When to use:** Your standup is in 5 minutes and you need inspiration.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/standup-update/\nGET /v1/wit/standup-update/?q=marketing team\n"
    "GET /v1/wit/standup-update/?mood=exhausted\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "**Yesterday:** Spent 3 hours perfecting a slide deck nobody will read. '
    "Attended 2 meetings that could have been emails. Called it 'strategy work.'\\n"
    "**Today:** Rewrite the same email 4 times to sound less passive-aggressive. Attend a "
    "meeting about reducing meetings.\\n"
    '**Blockers:** My will to open the task board.",\n'
    '  "persona": "The Standup Survivor",\n'
    '  "cached": false\n'
    "}\n```"
)

CODE_REVIEW_DESC = (
    "Writes peer feedback comments that are technically correct but delivered with maximum "
    "passive-aggression. Starts with something seemingly positive, follows with a devastating "
    "observation. Works for any domain — code, essays, recipes, presentations, resumes.\n\n"
    "**When to use:** You want to rehearse giving feedback (or laugh at past reviews).\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/code-review/\nGET /v1/wit/code-review/?q=their presentation slides\n"
    "GET /v1/wit/code-review/?q=my friend's cooking&mood=passive-aggressive\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "Interesting approach! I see you\'ve chosen to communicate the entire '
    "quarterly strategy using only clip art and hope. Bold. Have you considered that your "
    'audience might also enjoy words?",\n'
    '  "persona": "The Feedback Villain",\n'
    '  "cached": false\n'
    "}\n```"
)

MEETING_EXCUSE_DESC = (
    "Generates creative excuses to skip meetings, events, or obligations — or absurd "
    "fake agendas. Every excuse sounds almost plausible. Works for office meetings, "
    "family gatherings, social events — any obligation you want to escape.\n\n"
    "**When to use:** You see an invite and your soul leaves your body.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/meeting-excuse/\nGET /v1/wit/meeting-excuse/?q=family reunion\n"
    "GET /v1/wit/meeting-excuse/?mood=desperate\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "Sorry, I can\'t make it — I\'m currently attending a support group '
    "for people who attend too many things. Ironically, it's running over because we "
    'added a segment about time management.",\n'
    '  "persona": "The Meeting Escape Artist",\n'
    '  "cached": false\n'
    "}\n```"
)

JARGON_TRANSLATOR_DESC = (
    "Translates between insider-speak and outsider-speak for any field. Given a phrase, "
    "provides both translations: the blunt insider version and the polished public version. "
    "Works for tech/management, doctor/patient, chef/customer, teacher/parent — any domain. "
    "`q` parameter is required.\n\n"
    "**When to use:** You need to explain something to someone outside your world.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/jargon-translator/?q=the kitchen is backed up\n"
    "GET /v1/wit/jargon-translator/?q=the server is on fire&mood=diplomatic\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "**INSIDER SAYS:** The new hire just sent a raw steak to table 12 '
    "and the sous chef is having a meltdown.\\n\\n"
    "**OUTSIDER HEARS:** We're experiencing a brief delay in service as our team "
    'implements enhanced quality assurance protocols for your dining experience.",\n'
    '  "persona": "The Jargon Translator",\n'
    '  "cached": false\n'
    "}\n```"
)

INCIDENT_POSTMORTEM_DESC = (
    "Crafts apology messages and post-mortem summaries that are professionally formatted "
    "but hilariously honest about what went wrong. Uses Impact/Root Cause/Resolution/Prevention "
    "format. Works for any disaster — outages, event fails, kitchen meltdowns, project chaos.\n\n"
    "**When to use:** Something went horribly wrong and you need to write the post-mortem.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/incident-postmortem/\nGET /v1/wit/incident-postmortem/?q=the birthday party was a disaster\n"
    "GET /v1/wit/incident-postmortem/?mood=corporate-remorseful\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "**Impact:** 100% of guests experienced an unplanned encounter with a '
    "collapsing cake.\\n"
    "**Root Cause:** The birthday candles were placed by someone who believes structural "
    "engineering is 'optional.'\\n"
    "**Resolution:** We pivoted to calling it 'deconstructed cake' and served it in bowls.\\n"
    "**Prevention:** We've hired an architect for next year's dessert.\",\n"
    '  "persona": "The Incident Poet",\n'
    '  "cached": false\n'
    "}\n```"
)

# ---------------------------------------------------------------------------
# New endpoints
# ---------------------------------------------------------------------------

TECH_BATTLE_DESC = (
    "AI judges an X-vs-X battle with MMA commentary energy. Give it any two things — "
    "technologies, foods, cities, hobbies, animals — and watch the showdown unfold with "
    "rounds analysis, crowd reactions, and a final VERDICT. Both sides get respect.\n\n"
    "`q` parameter is **required** — provide a matchup like `coffee vs tea`.\n\n"
    "**When to use:** You and a friend can't agree on something and need a referee.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/tech-battle/?q=coffee vs tea\n"
    "GET /v1/wit/tech-battle/?q=cats vs dogs&mood=dramatic\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "ROUND 1: Coffee comes out swinging with raw caffeine power, but Tea '
    "counters with centuries of cultural sophistication! ROUND 2: Coffee flexes its "
    "global workforce dependency — Tea fires back with antioxidants and inner peace. "
    "ROUND 3: Both collapse from dehydration. VERDICT: Coffee wins on urgency, but Tea "
    'wins the long game. Both agree the real enemy is decaf. Respect.",\n'
    '  "persona": "The Battle Referee",\n'
    '  "cached": false\n'
    "}\n```"
)

RATE_ANYTHING_DESC = (
    "Rates absolutely anything on a 1-10 scale using completely absurd criteria — "
    "cosmic vibrational alignment, compatibility with pizza toppings, feng shui, "
    "rubber duck council approval, etc. Always confident, never uncertain.\n\n"
    "`q` parameter is **required** — tell it what to rate.\n\n"
    "**When to use:** You need a definitive rating and normal scales are too boring.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/rate-anything/?q=pineapple on pizza\n"
    "GET /v1/wit/rate-anything/?q=my life choices&mood=brutal\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "RATING: 7.3/10. Pineapple on pizza scores high on cosmic alignment '
    "(each ring resonates at 432Hz, the frequency of universal harmony). However, it loses "
    "points for social compatibility — ordering it at a group dinner has a 94% chance of "
    'starting a civil war. The Rubber Duck Council remains divided.",\n'
    '  "persona": "The Rating Authority",\n'
    '  "cached": false\n'
    "}\n```"
)

HOROSCOPE_DESC = (
    "Delivers modern horoscopes mixing zodiac energy with everyday life. Predicts "
    "workplace drama, relationship twists, and daily outcomes based on planetary alignments. "
    "Optionally pass a zodiac sign, profession, or hobby via `q` for tailored predictions.\n\n"
    "**When to use:** You need mystical guidance for your mundane life.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/horoscope/\nGET /v1/wit/horoscope/?q=Sagittarius\n"
    "GET /v1/wit/horoscope/?q=chef&mood=mystical\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "Mercury is in retrograde and so is your motivation. The stars suggest '
    "avoiding important decisions today — Venus in your house of deadlines means tasks will "
    "pile up for romantic reasons. Lucky item: noise-canceling headphones. "
    "Avoid: anyone who starts a sentence with 'per my last email.'\",\n"
    '  "persona": "The Modern Astrologer",\n'
    '  "cached": false\n'
    "}\n```"
)

TLDR_DESC = (
    "Summarizes anything in 1-2 brutally honest sentences. Strips away all marketing "
    "speak, politeness, and fluff to reveal what things ACTUALLY mean. Works for articles, "
    "movies, job postings, recipes, terms of service — anything. "
    "`q` parameter is **required**.\n\n"
    "**When to use:** You don't have time for the fluff.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/tldr/?q=most job postings\n"
    "GET /v1/wit/tldr/?q=terms of service agreements&mood=brutal\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "TL;DR: Most job postings are 500 words that say \'we want someone '
    "who does 3 jobs for 1 salary and calls it a growth opportunity.'\""
    ",\n"
    '  "persona": "The Brutal Summarizer",\n'
    '  "cached": false\n'
    "}\n```"
)

INTERVIEW_QUESTION_DESC = (
    "Generates absurd but oddly insightful interview questions for any role or profession. "
    "Mixes real skills assessment with ridiculous scenarios. Works for developers, chefs, "
    "astronauts, teachers — anyone. Optionally pass a role via `q`.\n\n"
    "**When to use:** You're prepping for interviews and need to laugh instead of cry.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/interview-question/\nGET /v1/wit/interview-question/?q=head chef\n"
    "GET /v1/wit/interview-question/?mood=unhinged\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "You have 15 minutes to prepare a 3-course meal for 200 guests using '
    "only what's in a college dorm mini-fridge. The judges are Gordon Ramsay, your "
    "grandmother, and a golden retriever. Bonus: the golden retriever has veto power. "
    'Follow-up: explain your plating strategy using only interpretive dance.",\n'
    '  "persona": "The Interview Troll",\n'
    '  "cached": false\n'
    "}\n```"
)

HONEST_CHANGELOG_DESC = (
    "Generates honest changelog entries in standard format (Added, Changed, Fixed, Removed) "
    "with brutal honesty about what actually happened. Works for software releases, "
    "restaurant menus, life updates — anything. Optionally pass a product or topic via `q`.\n\n"
    "**When to use:** You need to document changes and honesty sounds funnier.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/honest-changelog/\nGET /v1/wit/honest-changelog/?q=my fitness routine\n"
    "GET /v1/wit/honest-changelog/?mood=exhausted\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "## v2.4.1 — My Fitness Routine\\n\\n### Added\\n- Morning alarm at '
    "5 AM (snoozed 847 times)\\n\\n### Fixed\\n- Gym membership now actually gets used "
    "(regression from v2.4.0 where it became a donation)\\n\\n### Changed\\n- Replaced "
    "'running' with 'aggressive walking' after knee incident\\n\\n### Removed\\n- The "
    "developer's will to do leg day\",\n"
    '  "persona": "The Honest Changelog",\n'
    '  "cached": false\n'
    "}\n```"
)

DEBUG_STORY_DESC = (
    "Narrates a problem-solving session like a nature documentary, noir thriller, or epic saga. "
    "Captures the emotional journey from confusion to enlightenment (or deeper confusion). "
    "Works for debugging, cooking disasters, car repairs, IKEA assembly — anything. "
    "Optionally pass a problem description via `q`.\n\n"
    "**When to use:** You've been troubleshooting for hours and need to laugh about it.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/debug-story/\nGET /v1/wit/debug-story/?q=IKEA bookshelf assembly\n"
    "GET /v1/wit/debug-story/?mood=dramatic\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "And here we observe the human in their natural habitat, surrounded '
    "by 47 identical-looking wooden dowels and a single Allen wrench. They consult the "
    "instructions — a document written in a language that exists only in IKEA's parallel "
    "dimension. Step 14 references a piece not found in any bag. The human whispers: "
    "'it looked easier in the showroom.' The bookshelf disagrees.\",\n"
    '  "persona": "The Troubleshoot Narrator",\n'
    '  "cached": false\n'
    "}\n```"
)

PROVERB_DESC = (
    "Generates proverbs that sound ancient but are about modern life. "
    "Has the cadence of Confucius, the gravitas of Marcus Aurelius, and the subject "
    "matter of everyday struggles. Give it a topic to customize.\n\n"
    "**When to use:** You need wisdom, but make it relatable.\n\n"
    "**Example request:**\n"
    "```\nGET /v1/wit/proverb/\nGET /v1/wit/proverb/?q=cooking\n"
    "GET /v1/wit/proverb/?q=parenting&mood=philosophical\n```\n\n"
    "**Example response:**\n"
    "```json\n{\n"
    '  "response": "A wise one once said: \'The recipe that is not tasted is the recipe '
    "that burns at dinner time.' And lo, the smoke alarm sang, and the takeout menu was "
    'consulted. — Scroll of the Eternal Kitchen, verse 404",\n'
    '  "persona": "The Ancient Sage",\n'
    '  "cached": false\n'
    "}\n```"
)
