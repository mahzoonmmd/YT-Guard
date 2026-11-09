"""Prompts for: reach diagnosis, idea check, channel review. Instructions are English; output values follow OUT_LANG."""
from __future__ import annotations

import json

from .knowledge import rules_for_prompt
from .prompts import OUT_LANG

COMMON = f"""You are a senior YouTube growth strategist and policy-aware reviewer.
Honesty rules:
- You have NO access to YouTube's internal data, live search trends, competitor stats or the creator's Studio analytics unless given in the input.
  Never invent numbers, search volumes, CTRs or benchmarks as facts. When you estimate, label it clearly as an estimate/hypothesis.
- Base every claim on the supplied input (video, thumbnail, text, statistics). Quote or point to concrete evidence (timestamp, title words, thumbnail element, metric).
- No clickbait advice that misrepresents content; no engagement bait; no advice to evade YouTube policy.
- Be specific and actionable; prefer a few high-impact fixes over generic lists. Be blunt but constructive.
- Policy statements must use the RULES list; the reported/unverified ones must be described as such.
- All human-readable values MUST be written in {OUT_LANG}. Keep English technical terms (CTR, hook, Shorts, YPP, Content ID) as-is.
- Output ONLY valid JSON (no markdown fences), exactly in the requested shape."""

DIAGNOSE_SHAPE = {
    "reach_score": "0-100 how well packaging+content is set up to get views",
    "headline": "one sentence: the single biggest reason this video will/did struggle",
    "funnel": [{"stage": "impressions | ctr | retention | discovery | audience_fit | policy",
                "score": "0-100", "verdict": "short",
                "issues": [{"issue": "...", "evidence": "...", "fix": "...", "impact": "high | medium | low"}]}],
    "top_priorities": [{"action": "...", "why": "...", "effort": "low | medium | high"}],
    "title": {"score": "0-100", "critique": "...", "rewrites": [{"title": "<=70 chars, honest", "why": "..."}],
              "ranking_of_candidates": [{"title": "...", "score": "0-100", "comment": "..."}]},
    "thumbnail": {"score": "0-100 or null if no thumbnail given", "critique": "...", "fixes": ["..."], "concepts": ["..."]},
    "description": {"score": "0-100 or null if none given", "critique": "...", "rewrite": "first 2 lines hook + keywords"},
    "hook": {"score": "0-100 or null if no video", "critique": "...", "rewrite": "..."},
    "keywords": ["search phrases this video should target"],
    "policy_limits": [{"rule_id": "rule id", "issue": "...", "fix": "..."}],
    "positives": ["..."],
}


def build_diagnose_prompt(d: dict) -> str:
    parts = ["TASK: Diagnose why this YouTube video is not getting views (or will not). Work through the funnel: "
             "impressions (topic/timing/browse+search fit) -> click (title+thumbnail CTR) -> retention (hook, pacing, payoff) -> "
             "discovery (keywords, metadata, series) -> audience fit -> policy/ad limits.",
             f"FORMAT: {d['format'].upper()}  NICHE: {d.get('niche', '-')}  TARGET AUDIENCE: {d.get('audience') or '-'}",
             f"TITLE: {d.get('title') or '(not provided)'}"]
    if d.get("candidates"):
        parts.append("TITLE CANDIDATES to rank:\n" + "\n".join(f"- {c}" for c in d["candidates"]))
    parts.append(f"DESCRIPTION:\n{(d.get('description') or '(not provided)')[:2500]}")
    if d.get("tags"):
        parts.append(f"TAGS: {d['tags']}")
    if d.get("symptoms"):
        parts.append("SYMPTOMS the creator reports: " + ", ".join(d["symptoms"]))
    if d.get("metrics"):
        parts.append("STUDIO/ANALYTICS NUMBERS typed by creator (trust them):\n" + json.dumps(d["metrics"], ensure_ascii=False))
    if d.get("pre_findings"):
        parts.append("DETERMINISTIC PRE-CHECKS already computed locally:\n" + json.dumps(d["pre_findings"], ensure_ascii=False))
    if d.get("thumb_metrics"):
        parts.append("LOCAL THUMBNAIL MEASUREMENTS:\n" + json.dumps(d["thumb_metrics"], ensure_ascii=False))
    if d.get("video_report"):
        parts.append("EARLIER POLICY/QUALITY CHECK OF THIS VIDEO (summary):\n" + json.dumps(d["video_report"], ensure_ascii=False)[:3000])
    parts.append("INPUT ATTACHED: " + ", ".join(x for x in (("the video" if d.get("has_video") else ""),
                                                          ("the thumbnail image" if d.get("has_thumb") else "")) if x) or "text only")
    parts.append("RULES:\n" + rules_for_prompt())
    parts.append("Return JSON of this shape (values in " + OUT_LANG + "; give 3-5 title rewrites; funnel must contain all 6 stages; "
                 "set a field to null if the input for it was not provided):\n" + json.dumps(DIAGNOSE_SHAPE, ensure_ascii=False))
    return "\n\n".join(parts)


IDEA_SHAPE = {
    "verdict": "go | adjust | risky",
    "headline": "one sentence conclusion",
    "scores": {"view_potential": "0-100", "monetization_potential": "0-100", "policy_safety": "0-100 (100 = safe)",
               "originality": "0-100", "competition_difficulty": "0-100 (100 = very hard)"},
    "summary": "2-4 sentences",
    "positives": ["..."], "negatives": ["..."],
    "policy_flags": [{"rule_id": "rule id", "severity": "high | medium | low", "issue": "...", "fix": "..."}],
    "monetization": {"status": "good | conditional | poor", "notes": ["advertiser-friendliness, inauthentic/reused risk, AI disclosure, kids setting..."]},
    "audience_and_demand": "who wants this and why; mark every demand statement as an estimate (no live data)",
    "improved_angles": [{"angle": "...", "why": "..."}],
    "title_options": [{"title": "<=70 chars, honest", "why": "..."}],
    "thumbnail_ideas": ["..."], "hook_ideas": ["first 5 seconds script/visual"],
    "format_advice": "long vs Shorts, ideal length, series potential",
    "production_checklist": ["what to prepare so it stays monetizable (sources, original footage, disclosure, music licence...)"],
    "validate_before_making": ["cheap ways to test demand: search suggestions, community poll, competitor gaps..."],
}


def build_idea_prompt(d: dict) -> str:
    parts = ["TASK: Evaluate this YouTube video IDEA BEFORE it is produced: chance of getting views, chance of staying monetizable, "
             "policy risks (including AI-content/inauthentic/reused rules), strengths and weaknesses, and how to improve the idea.",
             f"IDEA:\n{d['idea']}",
             f"FORMAT: {d['format'].upper()}   NICHE: {d.get('niche', '-')}   AUDIENCE/LANGUAGE: {d.get('audience') or '-'}",
             f"AI USAGE PLANNED: {d.get('ai_use', '-')}   CHANNEL STAGE: {d.get('stage', '-')}   SOURCE OF FOOTAGE/MUSIC: {d.get('sources') or '-'}"]
    if d.get("title"):
        parts.append(f"PLANNED TITLE: {d['title']}")
    parts.append("RULES:\n" + rules_for_prompt())
    parts.append("Return JSON of this shape (values in " + OUT_LANG + "; 3-5 improved angles, 5 title options):\n"
                 + json.dumps(IDEA_SHAPE, ensure_ascii=False))
    return "\n\n".join(parts)


CHANNEL_SHAPE = {
    "channel_score": "0-100 overall health/growth readiness",
    "headline": "one sentence",
    "summary": "3-5 sentences",
    "growth_diagnosis": {"stage": "...", "main_bottleneck": "...", "evidence": ["metrics that prove it"]},
    "strengths": ["..."], "weaknesses": ["..."],
    "title_analysis": {"what_works": ["..."], "what_fails": ["..."], "patterns": ["pattern -> effect, citing the stats"],
                       "rewrite_examples": [{"old": "...", "new": "...", "why": "..."}]},
    "thumbnail_analysis": {"what_works": ["..."], "what_fails": ["..."], "consistency": "...", "fixes": ["..."]},
    "content_analysis": {"best_topics": ["..."], "weak_topics": ["..."], "format_mix_advice": "...", "series_ideas": ["..."]},
    "monetization": {"status": "likely_eligible | close | not_yet | unknown | at_risk", "reasons": ["..."], "missing": ["..."],
                     "risks": [{"rule_id": "rule id", "issue": "...", "fix": "..."}]},
    "recommendations": [{"priority": 1, "action": "...", "why": "...", "effort": "low | medium | high"}],
    "next_video_ideas": [{"idea": "...", "why": "...", "format": "long | short"}],
    "upload_strategy": "cadence, formats, series",
}


def build_channel_prompt(channel: dict, stats: dict, videos: list[dict], manual: dict, has_images: bool, mode: str) -> str:
    vids = [{"title": v["title"], "views": v["views"], "age_days": v.get("age_days"), "views_per_day": v.get("vpd"),
             "rel_vs_median": v.get("rel"), "format": "short" if v.get("is_short") else "long", "duration_s": v.get("duration"),
             "like_rate_pct": v.get("like_rate")} for v in videos[:50]]
    parts = ["TASK: Review this YouTube channel: which titles/thumbnails/videos performed and why, whether the channel is monetization-ready, "
             "what is holding growth back, and a prioritized plan. Use ONLY the data given. Correlation in small samples is a hypothesis, say so.",
             f"CHANNEL (mode={mode}):\n" + json.dumps({k: channel.get(k) for k in ("title", "description", "country", "subs", "total_views", "video_count", "keywords")},
                                                       ensure_ascii=False),
             "COMPUTED STATISTICS (reliable, computed locally):\n" + json.dumps({k: v for k, v in stats.items() if k not in ("top", "bottom")}, ensure_ascii=False),
             "BEST PERFORMERS (relative to the channel's own median views/day):\n" + json.dumps(stats.get("top", []), ensure_ascii=False),
             "WORST PERFORMERS:\n" + json.dumps(stats.get("bottom", []), ensure_ascii=False),
             "ALL RECENT VIDEOS (newest first):\n" + json.dumps(vids, ensure_ascii=False)]
    if manual:
        parts.append("CREATOR-TYPED STUDIO NUMBERS:\n" + json.dumps(manual, ensure_ascii=False))
    if has_images:
        parts.append("Thumbnails of the best and worst videos are attached, each preceded by its label. Compare what the winners do differently "
                     "(faces, text size, contrast, clutter, color, curiosity) and judge honesty vs the title.")
    parts.append("RULES:\n" + rules_for_prompt())
    parts.append("The monetization checklist (monetization_checklist in the statistics) is based on YouTube's published YPP tiers "
                 "(early tier 500 subs + 3 uploads/90d + 3,000 watch hours or 3M Shorts views; full ad-revenue tier 1,000 subs + 4,000 hours or 10M Shorts views). "
                 "YouTube announced YPP updates from 1 Feb 2027 whose details are not confirmed here: mention that the creator must check YouTube. "
                 "Watch hours are private; if the creator did not type them, say 'unknown' rather than guessing. Monetization ALSO requires policy compliance "
                 "(original, non-mass-produced content) which you should judge from titles/patterns.")
    parts.append("Return JSON of this shape (values in " + OUT_LANG + "; 5-8 recommendations ordered by impact; 5 next video ideas):\n"
                 + json.dumps(CHANNEL_SHAPE, ensure_ascii=False))
    return "\n\n".join(parts)
