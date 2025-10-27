import argparse
import os
import sys
import time
import math
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests
from dateutil import parser as date_parser
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str, api_version: str = "2", timeout_seconds: int = 20):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = (email, api_token)
        self.session.headers.update({"Accept": "application/json"})
        self.api_version = api_version
        self.timeout_seconds = timeout_seconds

    def _api(self, path: str) -> str:
        return f"{self.base_url}/rest/api/{self.api_version}{path}"

    def get(self, path: str, params: Optional[Dict] = None) -> Dict:
        url = self._api(path)
        resp = self.session.get(url, params=params, timeout=self.timeout_seconds)
        if resp.status_code == 401:
            raise RuntimeError("Unauthorized (401). Check JIRA_EMAIL and JIRA_API_TOKEN.")
        if resp.status_code == 403:
            raise RuntimeError("Forbidden (403). Check permissions and project access.")
        if not resp.ok:
            raise RuntimeError(f"Jira GET {url} failed: {resp.status_code} {resp.text}")
        return resp.json()

    def search_issues(self, jql: str, fields: Optional[List[str]] = None, limit: int = 50, start_at: int = 0) -> Dict:
        params = {
            "jql": jql,
            "maxResults": limit,
            "startAt": start_at,
        }
        if fields:
            params["fields"] = ",".join(fields)
        return self.get("/search", params=params)

    def get_issue(self, key: str, fields: Optional[List[str]] = None) -> Dict:
        params = {}
        if fields:
            params["fields"] = ",".join(fields)
        return self.get(f"/issue/{key}", params=params)

    def get_comments(self, key: str, limit: int = 200) -> List[Dict]:
        # Paginate comments (Jira defaults to 50)
        comments: List[Dict] = []
        start_at = 0
        while True:
            data = self.get(f"/issue/{key}/comment", params={"startAt": start_at, "maxResults": min(100, limit - start_at)})
            values = data.get("comments", []) or data.get("value", []) or []
            comments.extend(values)
            if len(comments) >= limit or start_at + data.get("maxResults", 0) >= data.get("total", 0):
                break
            start_at += data.get("maxResults", 0)
        return comments

    def get_fields(self) -> List[Dict]:
        return self.get("/field")


def find_field_id(fields: List[Dict], target_names: List[str]) -> Optional[str]:
    target_lower = {n.lower() for n in target_names}
    for f in fields:
        name = str(f.get("name", "")).lower()
        if name in target_lower:
            return f.get("id")
    # Fuzzy contains
    for f in fields:
        name = str(f.get("name", "")).lower()
        for target in target_lower:
            if target in name:
                return f.get("id")
    return None


def load_config() -> Tuple[str, str, str, str]:
    base_url = os.environ.get("JIRA_BASE_URL", "").strip()
    email = os.environ.get("JIRA_EMAIL", "").strip()
    token = os.environ.get("JIRA_API_TOKEN", "").strip() or os.environ.get("JIRA_PASSWORD", "").strip()
    api_version = os.environ.get("JIRA_API_VERSION", "2").strip()
    if not base_url or not email or not token:
        raise RuntimeError("Missing JIRA config. Set JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN.")
    return base_url, email, token, api_version


def iso_to_dt(s: str) -> datetime:
    return date_parser.isoparse(s)


def within_last_days(dt: datetime, days: int, now: Optional[datetime] = None) -> bool:
    if now is None:
        now = datetime.now(timezone.utc)
    return dt >= now - timedelta(days=days)


def label_from_compound(compound: float) -> str:
    if compound > 0.05:
        return "positive"
    if compound < -0.05:
        return "negative"
    return "neutral"


def analyze_issue_sentiment(analyzer: SentimentIntensityAnalyzer, status_summary: Optional[str], comments_text: str) -> Tuple[float, Dict[str, float]]:
    # Weight Status Summary more than comments if both are present
    weights = []
    scores = []

    if status_summary and status_summary.strip():
        s = analyzer.polarity_scores(status_summary).get("compound", 0.0)
        scores.append(s)
        weights.append(0.6)

    if comments_text and comments_text.strip():
        s = analyzer.polarity_scores(comments_text).get("compound", 0.0)
        scores.append(s)
        weights.append(0.4)

    if not scores:
        return 0.0, {"compound": 0.0}

    # Weighted average
    compound = sum(s * w for s, w in zip(scores, weights)) / (sum(weights) or 1.0)
    # Also return raw combined sentiment for transparency
    return compound, {"compound": compound}


def extract_signals(text: str) -> Dict[str, bool]:
    t = (text or "").lower()
    risk_markers = [
        "risk", "blocked", "blocker", "delay", "slip", "slipped", "regression",
        "dependency", "dependent", "qa issue", "qe issue", "concern", "problem", "issue"
    ]
    positive_markers = [
        "landed", "merged", "shipped", "completed", "done", "progress", "on track",
        "green", "good", "improved", "started", "work has started"
    ]
    found_risk = any(m in t for m in risk_markers)
    found_positive = any(m in t for m in positive_markers)
    return {"risk_flag": found_risk, "positive_flag": found_positive}


def build_report(top_issue: Dict, child_issues: List[Dict], issue_to_details: Dict[str, Dict], days: int) -> str:
    analyzer = SentimentIntensityAnalyzer()

    per_issue_rows = []
    compounds = []
    risk_flags = 0
    positive_flags = 0

    def get_field(issue: Dict, fid: str) -> Optional[str]:
        fields = issue.get("fields", {})
        val = fields.get(fid)
        if isinstance(val, dict) and "value" in val:
            return val.get("value")
        if isinstance(val, str):
            return val
        return None

    # Aggregate across top issue and children
    all_issues = [top_issue] + child_issues
    for issue in all_issues:
        key = issue.get("key")
        fields = issue.get("fields", {})
        details = issue_to_details.get(key, {})
        status = fields.get("status", {}) or {}
        status_name = status.get("name")
        status_category = (status.get("statusCategory") or {}).get("name")

        status_summary_text = details.get("status_summary_text") or ""
        comments_text = details.get("comments_text") or ""
        compound, _scores = analyze_issue_sentiment(SentimentIntensityAnalyzer(), status_summary_text, comments_text)
        compounds.append(compound)
        label = label_from_compound(compound)

        signals = extract_signals(status_summary_text + "\n" + comments_text)
        if signals["risk_flag"]:
            risk_flags += 1
        if signals["positive_flag"]:
            positive_flags += 1

        updated = fields.get("updated") or ""
        per_issue_rows.append({
            "key": key,
            "summary": fields.get("summary"),
            "status": status_name,
            "statusCategory": status_category,
            "updated": updated,
            "sentiment": label,
            "sentiment_score": round(compound, 3),
            "has_recent_narrative": bool(status_summary_text.strip() or comments_text.strip()),
            "signals": signals
        })

    avg = (sum(compounds) / len(compounds)) if compounds else 0.0
    overall_label = label_from_compound(avg)

    # TL;DR
    tldr_lines = [
        f"Overall sentiment: {overall_label} (avg={avg:.2f}).",
        f"Signals: {positive_flags} positive markers; {risk_flags} risk markers across last {days} days."
    ]

    # Executive Summary
    have_narratives = sum(1 for r in per_issue_rows if r["has_recent_narrative"])
    exec_lines = []
    if overall_label == "positive":
        exec_lines.append("Sentiment trends positive with forward momentum.")
    elif overall_label == "negative":
        exec_lines.append("Sentiment trends negative with notable concerns.")
    else:
        exec_lines.append("Sentiment is mixed/neutral with uneven visibility.")

    exec_lines.append(
        f"{have_narratives} of {len(per_issue_rows)} items have recent narrative updates (Status Summary or comments)."
    )
    if risk_flags:
        exec_lines.append("Explicit risk language detected; ensure mitigation/owner and near-term follow-ups.")

    # Supporting Information
    sup_lines = []
    sup_lines.append("- Epic and in-progress children analyzed over last {} days:".format(days))
    for r in per_issue_rows:
        sup_lines.append(
            f"  - {r['key']}: {r['summary']} | {r['status']} ({r['statusCategory']}) | "
            f"updated {r['updated']} | sentiment {r['sentiment']} ({r['sentiment_score']}) | "
            f"recent narrative: {'yes' if r['has_recent_narrative'] else 'no'} | "
            f"signals: +{int(r['signals']['positive_flag'])}/-{int(r['signals']['risk_flag'])}"
        )

    report = []
    report.append("TL;DR")
    report.extend(f"- {line}" for line in tldr_lines)
    report.append("")
    report.append("Executive Summary")
    report.extend(exec_lines)
    report.append("")
    report.append("Supporting information")
    report.extend(sup_lines)

    return "\n".join(report)


def gather_data(
    client: JiraClient,
    top_key: str,
    days: int,
    status_summary_field_id: Optional[str],
    parent_link_field_id: Optional[str],
    epic_link_field_id: Optional[str],
) -> Tuple[Dict, List[Dict], Dict[str, Dict]]:
    fields = ["summary", "status", "updated"]
    if status_summary_field_id:
        fields.append(status_summary_field_id)

    # Fetch top issue
    top_issue = client.get_issue(top_key, fields=fields)

    # Build JQL to find open issues in hierarchy under the top issue
    jql_parts = []
    if parent_link_field_id:
        jql_parts.append(f'"cf[{parent_link_field_id.replace("customfield_", "")}]" = "{top_key}"')
    if epic_link_field_id:
        jql_parts.append(f'"cf[{epic_link_field_id.replace("customfield_", "")}]" = "{top_key}"')

    child_issues: List[Dict] = []
    if jql_parts:
        jql = "(" + " OR ".join(jql_parts) + ') AND statusCategory in ("In Progress")'
        search = client.search_issues(jql=jql, fields=fields, limit=100)
        child_issues = search.get("issues", [])
    else:
        # Fallback: try linkedIssues function (may be broad)
        jql = f'issue in linkedIssues("{top_key}") AND statusCategory in ("In Progress")'
        search = client.search_issues(jql=jql, fields=fields, limit=100)
        child_issues = search.get("issues", [])

    # For each issue, collect status summary text and last-week comments
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    def extract_status_summary_text(issue: Dict) -> str:
        if not status_summary_field_id:
            return ""
        fields_map = issue.get("fields", {})
        raw_val = fields_map.get(status_summary_field_id)
        if isinstance(raw_val, dict) and "value" in raw_val:
            return str(raw_val.get("value") or "")
        if isinstance(raw_val, str):
            return raw_val
        return ""

    keys = [top_issue.get("key")] + [i.get("key") for i in child_issues]
    details: Dict[str, Dict] = {}
    for key in keys:
        # Status Summary
        if key == top_issue.get("key"):
            issue = top_issue
        else:
            issue = next((i for i in child_issues if i.get("key") == key), None)
        status_summary_text = extract_status_summary_text(issue) if issue else ""

        # Comments
        comments_texts: List[str] = []
        try:
            comments = client.get_comments(key, limit=200)
        except Exception:
            comments = []
        for c in comments:
            created_raw = c.get("created") or c.get("createdDate")
            if not created_raw:
                continue
            try:
                created_dt = iso_to_dt(created_raw)
            except Exception:
                continue
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=timezone.utc)
            if created_dt >= cutoff:
                body = c.get("body") or ""
                comments_texts.append(str(body))

        details[key] = {
            "status_summary_text": status_summary_text or "",
            "comments_text": "\n".join(comments_texts) if comments_texts else "",
        }

    return top_issue, child_issues, details


def main():
    parser = argparse.ArgumentParser(description="Generate sentiment analysis report for a Jira issue hierarchy.")
    parser.add_argument("top_issue_key", help="Top Jira issue key (e.g., XCMSTRAT-1254)")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days for comments (default: 7)")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout seconds (default: 20)")
    args = parser.parse_args()

    try:
        base_url, email, token, api_version = load_config()
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(2)

    client = JiraClient(base_url, email, token, api_version=api_version, timeout_seconds=args.timeout)

    # Discover fields
    try:
        fields = client.get_fields()
    except Exception as e:
        print(f"Failed to fetch Jira fields: {e}", file=sys.stderr)
        sys.exit(2)

    # Allow overrides via env
    status_summary_field_id = os.environ.get("JIRA_STATUS_SUMMARY_FIELD_ID")
    parent_link_field_id = os.environ.get("JIRA_PARENT_LINK_FIELD_ID")
    epic_link_field_id = os.environ.get("JIRA_EPIC_LINK_FIELD_ID")

    if not status_summary_field_id:
        status_summary_field_id = find_field_id(fields, ["Status Summary", "Latest Status Summary"])
    if not parent_link_field_id:
        parent_link_field_id = find_field_id(fields, ["Parent Link"])
    if not epic_link_field_id:
        epic_link_field_id = find_field_id(fields, ["Epic Link"])

    try:
        top_issue, child_issues, issue_to_details = gather_data(
            client=client,
            top_key=args.top_issue_key,
            days=args.days,
            status_summary_field_id=status_summary_field_id,
            parent_link_field_id=parent_link_field_id,
            epic_link_field_id=epic_link_field_id,
        )
    except Exception as e:
        print(f"Failed to gather data: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        report = build_report(top_issue, child_issues, issue_to_details, days=args.days)
    except Exception as e:
        print(f"Failed to build report: {e}", file=sys.stderr)
        sys.exit(2)

    print(report)


if __name__ == "__main__":
    main()
