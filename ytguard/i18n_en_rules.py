# -*- coding: utf-8 -*-
"""English overrides for the rules knowledge base (applied in knowledge.py when the UI language is English)."""
RULES_EN = {
    "inauthentic_content": {
        "title": "Inauthentic content (mass-produced / repetitive)", "impact": "Monetization",
        "summary": "Template-like, repetitive, mass-produced videos that look the same (even if all yours) can get the whole channel rejected or demonetized. The review looks at the channel-wide pattern, not a single video.",
        "fix": "Give every video a different structure, narrative and visuals, and real added value (analysis, personal experience, creative editing)."},
    "unedited_ai_output": {
        "title": "Raw AI output (prompt-to-upload)", "impact": "Monetization",
        "summary": "Uploading AI output directly with no editing and no added value counts as inauthentic content. AI itself is not the problem; a video with no human input is.",
        "fix": "Put your own script, narration, editing and visual choices into it; add your own voice or real footage."},
    "ai_persona_expert": {
        "title": "AI persona posing as an expert (health/legal/finance/politics)", "impact": "Monetization",
        "summary": "A synthetic face or voice presenting itself as a medical, legal, financial or political expert is one of the categories of inauthentic content.",
        "fix": "Cite sources, state clearly that AI is used, avoid definitive professional advice; a real person narrating is better."},
    "synthetic_disclosure": {
        "title": "Altered or synthetic content disclosure", "impact": "Monetization + trust",
        "summary": "If realistic content was made or altered with AI and viewers could think it's real, you must tick “Altered or synthetic content” in Studio. From 27 May 2026 YouTube may also label it automatically. Disclosing alone doesn't reduce reach or monetization; repeated concealment can.",
        "fix": "In YouTube Studio during upload set Altered or synthetic content to Yes."},
    "reused_content": {
        "title": "Reused content", "impact": "Monetization",
        "summary": "Clips, films, series or videos from others without meaningful change and without original commentary/analysis, or re-streams. Compilations and reactions are only acceptable with added value.",
        "fix": "Add commentary, analysis, narrative editing and shorter clips; use licensed material or your own."},
    "copyright_music": {
        "title": "Copyrighted music / audio (Content ID)", "impact": "Revenue / reach",
        "summary": "Content ID detects music and clips by audio-visual fingerprint. The result is usually a Claim (revenue goes to the owner or the video is blocked); a Strike only follows a formal complaint. No AI or app can replace Content ID; we only show suspicions.",
        "fix": "Use YouTube Audio Library or clearly licensed music; for Shorts use YouTube's own music library."},
    "copyright_footage": {
        "title": "Footage / logos / characters owned by others", "impact": "Revenue / reach",
        "summary": "Films, series, games, sports, news, cartoon characters and brand logos without permission risk a Claim or takedown. “Fair use” is not guaranteed.",
        "fix": "Shorten clips, transform them meaningfully or find licensed replacements."},
    "other_platform_watermark": {
        "title": "Watermarks of other platforms (TikTok / Reels / CapCut)", "impact": "Reach",
        "summary": "Re-uploaded videos with other apps' watermarks signal recycled content and weaken Shorts distribution. Remove watermarks only from your own videos, not other people's.",
        "fix": "Export a watermark-free version from your editor."},
    "advertiser_friendly": {
        "title": "Advertiser-friendly content", "impact": "Ad revenue",
        "summary": "Strong profanity (especially in the first 7 seconds), graphic violence, adult content, drugs, sensitive/tragic topics, misinformation and weapons can trigger Limited ads (yellow icon).",
        "fix": "Remove/bleep sensitive parts or frame the topic educationally/journalistically; fill in the self-certification correctly after upload."},
    "misleading_metadata": {
        "title": "Misleading title/thumbnail (clickbait / spam & deceptive practices)", "impact": "Reach + monetization",
        "summary": "Promising what the video doesn't deliver, irrelevant thumbnails, fake giveaways, meaningless like/subscribe demands (engagement bait).",
        "fix": "Title and thumbnail must show exactly what is in the video."},
    "misinformation": {
        "title": "Misinformation (health / elections / …)", "impact": "Removal / restriction",
        "summary": "Dangerous medical claims, election misinformation or distorted crisis information can get a video removed or the channel restricted.",
        "fix": "Support claims with reliable sources and avoid unjustified certainty."},
    "made_for_kids": {
        "title": "“Made for Kids” setting (COPPA)", "impact": "Monetization + features",
        "summary": "For every video you must state whether it is made for kids. A wrong choice can bring penalties or restrictions. Kids' videos have no comments and no personalized ads.",
        "fix": "Set Audience accurately in Studio."},
    "paid_promotion": {
        "title": "Paid promotion / sponsorship", "impact": "Legal + trust",
        "summary": "If there is a sponsor or a free/paid product in the video you must tick “Includes paid promotion” (and follow your country's laws).",
        "fix": "Tick paid promotion and disclose the sponsor clearly."},
    "shorts_format": {
        "title": "Shorts format", "impact": "Reach",
        "summary": "Shorts must be vertical or square and at most 3 minutes. The hook in the first 1–3 seconds and a high “viewed vs swiped away” rate strongly affect distribution. For Shorts revenue, views in the last 90 days matter.",
        "fix": "Use 9:16 at 1080×1920, start fast, no silence/black frames."},
    "long_format": {
        "title": "Long video", "impact": "Ad revenue",
        "summary": "Videos over 8 minutes can have mid-roll ads (if monetized). Most important is audience retention and the first 30 seconds.",
        "fix": "Strong hook, steady pacing, cut slow parts, add chapters."},
    "technical_quality": {
        "title": "Technical quality (audio, picture, black frames)", "impact": "Audience retention",
        "summary": "Very quiet/loud audio, long silences, black frames, low resolution and a static picture make viewers leave (not a rule, but it directly affects views).",
        "fix": "Loudness around -14 LUFS, at least 1080p, remove silence and black frames."},
    "ypp_thresholds": {
        "title": "New YPP thresholds (reference only)", "impact": "Joining monetization",
        "summary": "According to one unofficial source: for new entrants from 1 Feb 2027, 8,000 watch hours or 20 million Shorts views in 90 days; current members must accept the new terms by 31 Jan 2027 and need 10 million Shorts views in 90 days for Shorts revenue. These numbers come from a single source and must be verified on YouTube itself.",
        "fix": "Check the official YouTube Partner Program page before deciding."},
    "channel_inactivity": {
        "title": "Channel inactivity (reference only)", "impact": "Monetization",
        "summary": "According to the same source, 6 months without an upload or Community post can remove monetization access.",
        "fix": "At least one upload/post every few weeks."},
}
CONFIDENCE_EN = {"official": "Official", "reported": "Reported (several sources)", "unverified": "Unverified (single source)"}
IMPACT_EN = {"high": "High", "medium": "Medium", "low": "Low", "info": "Info"}
NICHES_EN = {
    "general": "General / entertainment", "education": "Education", "tech": "Tech / software tutorials", "gaming": "Gaming",
    "music": "Music", "news": "News / politics / current events", "health": "Health / medical / fitness",
    "finance": "Finance / investing / crypto", "legal": "Legal", "kids": "Kids", "film": "Film / editing / cinema",
    "lifestyle": "Lifestyle / travel / food", "other": "Other",
}
