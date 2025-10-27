#!/usr/bin/env python3
# file: sentiment_exec_summary.py
import os
import sys
import time
import json
import math
import base64
import datetime as dt
from typing import Dict, List, Tuple, Any, Optional

import requests
from nltk.sentiment import SentimentIntensityAnalyzer

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "").rstrip("/")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")

SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "application/json",
    "Content-Type": "application/json"
})

def _auth_header() -> Dict[str, str]:
    token = base64.b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    return {"Authorization": f"Basic {token}"}

def _get(url: str, params: Dict[str, Any] = None) -> Any:
    resp = SESSION.get(url, headers=_auth_header(), params=params or {})
    resp.raise_for_status()
    return resp.json()

def _post(url: str, payload: Dict[str, Any]) -> Any:
    resp = SESSION.post(url, headers=_auth_header(), data=json.dumps(payload))
    resp.raise_for_status()
    return resp.json()

def jira_search_fields(keyword: str = "", limit: int = 200) -> List[Dict[str, Any]]:
    url = f"{JIRA_BASE_URL}/rest/api/2/field"
    fields = _get(url)
    if not keyword:
        return fields[:limit]
    keyword_lower = keyword.lower()
    return [f for f in fields if keyword_lower in f.get("name", "").lower()][:limit]

def find_field_id_by_name(name: str) -> Optional[str]:
    for f in jira_search_fields(name, limit=500):
        if f.get("name", "").lower() == name.lower():
            return f.get("id")
    return None

def jira_search_jql(jql: str, fields: List[str], limit: int = 50) -> List[Dict[str, Any]]:
    url = f"{JIRA_BASE_URL}/rest/api/2/search"
    start_at = 0
    results: List[Dict[str, Any]] = []
    while True:
        payload = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": min(50, limit - len(results)),
            "fields": fields
        }
        if payload["maxResults"] <= 0:
            break
        data = _post(url, payload)
        issues = data.get("issues", [])
        results.extend(issues)
        if len(issues) == 0 or len(results) >= limit:
            break
        start_at += len(issues)
    return results

def jira_get_issue(key: str, fields: List[str]) -> Dict[str, Any]:
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{key}"
    params = {"fields": ",".join(fields)}
    return _get(url, params)

def jira_get_all_comments(key: str, max_comments: int = 200) -> List[Dict[str, Any]]:
    url = f"{JIRA_BASE_URL}/rest/api/2/issue/{key}/comment"
    start_at = 0
    results: List[Dict[str, Any]] = []
    while True:
        params = {"startAt": start_at, "maxResults": min(50, max_comments - len(results))}
        data = _get(url, params)
        comments = data.get("comments", [])
        results.extend(comments)
        if len(comments) == 0 or len(results) >= max_comments:
            break
        start_at += len(comments)
    return results

def collect_in_progress_descendants(root_key: str, parent_link_field: str, max_depth: int = 3) -> List[str]:
    # BFS over "Parent Link" relationships, statuscategory = In Progress
    in_progress_clause = 'statuscategory in ("In Progress")'
    seen: set = set([root_key])
    frontier: List[Tuple[str, int]] = [(root_key, 0)]
    all_keys: List[str] = [root_key]
    while frontier:
        current, depth = frontier.pop(0)
        if depth >= max_depth:
            continue
        jql = f'"{parent_link_field}" = {current} AND {in_progress_clause}'
        for issue in jira_search_jql(jql, fields=["key"], limit=200):
            key = issue.get("key")
            if key and key not in seen:
                seen.add(key)
                all_keys.append(key)
                frontier.append((key, depth + 1))
    return all_keys

def filter_comments_last_days(comments: List[Dict[str, Any]], days: int) -> List[Dict[str, Any]]:
    cutoff = dt.datetime.utcnow() - dt.timedelta(days=days)
    filtered = []
    for c in comments:
        created_str = c.get("created")
        if not created_str:
            continue
        # Jira timestamps are ISO 8601 with timezone, parse minimally
        # Example: "2025-09-09T16:15:41.918+0000"
        try:
            created = dt.datetime.strptime(created_str[:23] + "+0000", "%Y-%m-%dT%H:%M:%S.%f+0000")
        except Exception:
            try:
                created = dt.datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(dt.timezone.utc).replace(tzinfo=None)
            except Exception:
                continue
        if created >= cutoff:
            filtered.append(c)
    return filtered

def init_vader() -> SentimentIntensityAnalyzer:
    # Ensure VADER lexicon is present (nltk auto-download can be added if needed)
    from nltk import download
    try:
        SentimentIntensityAnalyzer()
    except Exception:
        download("vader_lexicon")
    return SentimentIntensityAnalyzer()

def score_text(sia: SentimentIntensityAnalyzer, text: str) -> Dict[str, float]:
    if not text.strip():
        return {"neg": 0.0, "neu": 1.0, "pos": 0.0, "compound": 0.0}
    return sia.polarity_scores(text)

def label_from_compound(compound: float) -> str:
    if compound >= 0.2:
        return "positive"
    if compound <= -0.2:
        return "negative"
    return "neutral"

def has_risk_keywords(text: str) -> bool:
    t = text.lower()
    keywords = ["slip", "slipped", "delay", "delayed", "blocked", "overdue", "push", "pushed", "won't meet", "risk"]
    return any(k in t for k in keywords)

def analyze_issue(key: str, field_status_summary: Optional[str], field_latest_status_summary: Optional[str], days: int, sia: SentimentIntensityAnalyzer) -> Dict[str, Any]:
    fields = ["summary", "status", "priority", "assignee"]
    if field_status_summary:
        fields.append(field_status_summary)
    if field_latest_status_summary:
        fields.append(field_latest_status_summary)
    issue = jira_get_issue(key, fields)
    f = issue.get("fields", {})
    summary = f.get("summary")
    status = (f.get("status") or {}).get("name")
    priority = (f.get("priority") or {}).get("name")
    assignee = ((f.get("assignee") or {}).get("displayName")) or "Unassigned"

    ss_text = ""
    if field_status_summary and f.get(field_status_summary):
        # Custom fields may return scalar or object; normalize to string
        val = f.get(field_status_summary)
        if isinstance(val, dict) and "value" in val:
            ss_text = (val.get("value") or "") or ""
        else:
            ss_text = str(val or "").strip()

    lss_text = ""
    if field_latest_status_summary and f.get(field_latest_status_summary):
        val = f.get(field_latest_status_summary)
        if isinstance(val, dict) and "value" in val:
            lss_text = (val.get("value") or "") or ""
        else:
            lss_text = str(val or "").strip()

    comments = jira_get_all_comments(key, max_comments=200)
    recent_comments = filter_comments_last_days(comments, days)
    comments_text = "\n".join([c.get("body") or "" for c in recent_comments])

    combined_text = "\n".join([ss_text, lss_text, comments_text]).strip()
    s_ss = score_text(sia, ss_text)
    s_cmts = score_text(sia, comments_text)
    s_all = score_text(sia, combined_text)

    risk = has_risk_keywords(combined_text)
    label = label_from_compound(s_all.get("compound", 0.0))

    return {
        "key": key,
        "summary": summary,
        "status": status,
        "priority": priority,
        "assignee": assignee,
        "status_summary": ss_text or None,
        "latest_status_summary": lss_text or None,
        "recent_comments_count": len(recent_comments),
        "sentiment": {
            "status_summary": s_ss,
            "comments_last_week": s_cmts,
            "combined": s_all,
            "label": label,
            "risk_keywords": risk
        }
    }

def build_exec_summary(analyses: List[Dict[str, Any]]) -> str:
    if not analyses:
        return "No in-progress issues found; no sentiment to report."

    labels = [a["sentiment"]["label"] for a in analyses]
    pos = labels.count("positive")
    neg = labels.count("negative")
    neu = labels.count("neutral")
    risks = [a for a in analyses if a["sentiment"]["risk_keywords"]]

    trend = "positive" if pos >= max(neg, neu) else ("neutral" if neu >= max(pos, neg) else "mixed")
    parts: List[str] = []
    parts.append(f"Overall sentiment {trend}: {pos} positive, {neu} neutral, {neg} negative across {len(analyses)} issues.")
    if risks:
        risk_keys = ", ".join(sorted(a["key"] for a in risks))
        parts.append(f"Risks mentioned in: {risk_keys}.")
    # Call out any negative issues explicitly
    negatives = [a for a in analyses if a["sentiment"]["label"] == "negative"]
    if negatives:
        parts.append("Watch items: " + ", ".join(f'{a["key"]} ({a["summary"]})' for a in negatives))

    return " ".join(parts)

def main():
    if not (JIRA_BASE_URL and JIRA_EMAIL and JIRA_API_TOKEN):
        print("Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN environment variables.", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python sentiment_exec_summary.py XCMSTRAT-1338 [--days 7]", file=sys.stderr)
        sys.exit(2)

    root_key = sys.argv[1]
    days = 7
    if "--days" in sys.argv:
        try:
            days = int(sys.argv[sys.argv.index("--days") + 1])
        except Exception:
            pass

    # Resolve field IDs dynamically
    parent_link_field_id = find_field_id_by_name("Parent Link")
    status_summary_field_id = find_field_id_by_name("Status Summary")
    latest_status_summary_field_id = find_field_id_by_name("Latest Status Summary")

    if not parent_link_field_id:
        print('Failed to resolve "Parent Link" field ID.', file=sys.stderr)
        sys.exit(3)

    in_progress_keys = collect_in_progress_descendants(root_key, parent_link_field_id, max_depth=4)

    sia = init_vader()
    analyses: List[Dict[str, Any]] = []
    for key in in_progress_keys:
        try:
            a = analyze_issue(key, status_summary_field_id, latest_status_summary_field_id, days, sia)
            # Only include truly in-progress issues (root included regardless)
            if key == root_key or (a.get("status") == "In Progress"):
                analyses.append(a)
        except requests.HTTPError as e:
            print(f"Warn: failed to analyze {key}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warn: unexpected error on {key}: {e}", file=sys.stderr)

    # Print per-issue results
    print(json.dumps({"issues": analyses}, indent=2))

    # Print exec summary
    summary = build_exec_summary(analyses)
    print("\n=== Executive Summary ===")
    print(summary)

if __name__ == "__main__":
    main()