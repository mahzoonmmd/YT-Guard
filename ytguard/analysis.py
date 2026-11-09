"""Merges local checks + questionnaire rules + AI output into one report."""
from __future__ import annotations

import time
from pathlib import Path

from .knowledge import RULES, SEV_ORDER

PTS = {"high": 18, "medium": 8, "low": 3, "info": 0}


def _sev(s) -> str:
    s = str(s or "low").lower()
    return s if s in SEV_ORDER else "low"


def normalize_ai(raw: dict) -> dict:
    def lst(x):
        return x if isinstance(x, list) else []

    def num(x, d=0.0):
        try:
            return float(x)
        except Exception:
            return d

    disc = raw.get("disclosure") if isinstance(raw.get("disclosure"), dict) else {}
    ret = raw.get("retention") if isinstance(raw.get("retention"), dict) else {}
    ai_usage = raw.get("ai_usage") if isinstance(raw.get("ai_usage"), dict) else {}
    findings = []
    for f in lst(raw.get("findings")):
        if not isinstance(f, dict):
            continue
        rid = f.get("rule_id") if f.get("rule_id") in RULES else "technical_quality"
        ts = f.get("timestamp")
        findings.append({"rule_id": rid, "severity": _sev(f.get("severity")), "issue": str(f.get("issue", "")).strip(),
                         "evidence": str(f.get("evidence", "") or ""), "fix": str(f.get("fix", "") or ""),
                         "timestamp": None if str(ts).lower() in ("none", "null", "") else ts, "source": "ai"})
    fq = []
    for i, q in enumerate(lst(raw.get("follow_up_questions"))[:4]):
        if isinstance(q, dict) and q.get("question"):
            fq.append({"id": str(q.get("id") or f"q{i+1}"), "question": str(q["question"]), "why": str(q.get("why", "")),
                       "options": [str(o) for o in lst(q.get("options"))][:5]})
    return {
        "detected_format": str(raw.get("detected_format", "")).lower(),
        "summary": str(raw.get("summary", "")),
        "language_of_video": str(raw.get("language_of_video", "")),
        "overall_risk_score": max(0, min(100, num(raw.get("overall_risk_score"), 0))),
        "ai_usage": {"likely_ai_voice": bool(ai_usage.get("likely_ai_voice")),
                     "likely_ai_visuals": bool(ai_usage.get("likely_ai_visuals")),
                     "likely_ai_music": bool(ai_usage.get("likely_ai_music")),
                     "realistic_enough_to_mislead": bool(ai_usage.get("realistic_enough_to_mislead")),
                     "confidence": max(0.0, min(1.0, num(ai_usage.get("confidence")))),
                     "evidence": str(ai_usage.get("evidence", ""))},
        "disclosure": {"required": str(disc.get("required", "maybe")).lower(), "reason": str(disc.get("reason", "")),
                       "suggested_description_text": str(disc.get("suggested_description_text", ""))},
        "findings": findings,
        "copyright_suspects": [c for c in lst(raw.get("copyright_suspects")) if isinstance(c, dict)],
        "retention": {"hook_score": num(ret.get("hook_score"), 0), "hook_comment": str(ret.get("hook_comment", "")),
                      "notes": [n for n in lst(ret.get("notes")) if isinstance(n, dict)]},
        "positives": [str(p) for p in lst(raw.get("positives"))],
        "follow_up_questions": fq,
    }


def compute_score(findings: list[dict], ai_score: float | None) -> tuple[int, str, int]:
    pts = sum(PTS[f["severity"]] for f in findings if f.get("source") != "ai")
    pts = min(pts, 60)
    if ai_score is not None:
        score = min(100, round(ai_score + 0.5 * pts))
    else:
        score = min(100, round(pts * 1.3))
    if any(f["severity"] == "high" for f in findings) and score < 45:
        score = 45
    verdict = "safe" if score < 25 else ("caution" if score < 55 else "risky")
    return score, verdict, pts


def assemble_report(*, path: str, fmt: str, answers: dict, local: dict, q_findings: list[dict],
                    ai: dict | None, ai_error: str = "", provider: str = "", model: str = "") -> dict:
    findings = list(local["findings"]) + list(q_findings) + (list(ai["findings"]) if ai else [])
    findings = [f for f in findings if f.get("issue")]
    findings.sort(key=lambda f: -SEV_ORDER[f["severity"]])
    score, verdict, pts = compute_score(findings, ai["overall_risk_score"] if ai else None)
    return {
        "version": 1, "name": Path(path).name, "path": path, "ts": time.time(), "format": fmt,
        "answers": answers, "info": local["info"], "metrics": local["metrics"], "audio": local["audio"],
        "meta": local["meta"], "local_findings": local["findings"], "q_findings": q_findings,
        "ai": ai, "ai_error": ai_error, "provider": provider, "model": model,
        "findings": findings, "score": score, "verdict": verdict, "local_points": pts,
    }


VERDICT_FA = {"safe": "ریسک کم", "caution": "نیاز به بازبینی", "risky": "ریسک بالا"}
