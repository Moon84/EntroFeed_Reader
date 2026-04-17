# -*- coding: utf-8 -*-
"""RSSHub route discovery utility using RSSHub-Radar rules."""

import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

# Load rules from RSSHub-Radar JSON file
RULESPATH = Path(__file__).parent.parent.parent / "data" / "radar-rules.json"

# Cache for rules
_rules_cache: Optional[Dict[str, Any]] = None


def _load_rules() -> Dict[str, Any]:
    """Load RSSHub-Radar rules from JSON file."""
    global _rules_cache
    if _rules_cache is not None:
        return _rules_cache

    if RULESPATH.exists():
        with open(RULESPATH, "r", encoding="utf-8") as f:
            _rules_cache = json.load(f)
    else:
        _rules_cache = {}
    return _rules_cache


def _extract_domain(url: str) -> tuple:
    """Extract subdomain and domain from URL.

    Returns (subdomain, full_domain) where full_domain includes TLD.
    Examples:
      twitter.com -> ("", "twitter.com")
      www.twitter.com -> ("www", "twitter.com")
      x.com -> ("", "x.com")
      user.name.example.com -> ("user.name", "example.com")
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        parts = hostname.split(".")

        if len(parts) >= 2:
            if len(parts) == 2:
                return ("", parts[0] + "." + parts[1])
            elif len(parts) == 3:
                return (parts[0], parts[1] + "." + parts[2])
            else:
                return (parts[0], ".".join(parts[-2:]))
        return ("", hostname)
    except Exception:
        return ("", "")


def _match_path(source_pattern: str, path: str) -> Optional[Dict[str, str]]:
    """Match a URL path against a source pattern and extract params."""
    regex_pattern = re.sub(r":(\w+)\?", r"(?P<\1>[^/]*)?", source_pattern)
    regex_pattern = re.sub(r":(\w+)", r"(?P<\1>[^/]+)", regex_pattern)
    regex_pattern = f"^{regex_pattern}$"

    match = re.match(regex_pattern, path)
    if match:
        return {k: v for k, v in match.groupdict().items() if v is not None}
    return None


def _apply_target_template(template: str, params: Dict[str, str]) -> str:
    """Apply extracted params to target template."""
    result = template
    for key, value in params.items():
        result = result.replace(f":{key}", value)
        result = re.sub(rf"/:{key}\?", f"/{value}" if value else "", result)
    result = re.sub(r":\w+\??", "", result)
    return result


def discover_rsshub_routes(url: str) -> List[Dict[str, Any]]:
    """Discover available RSSHub routes for a given URL."""
    rules = _load_rules()
    results = []

    subdomain, domain = _extract_domain(url)
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"

    if domain not in rules:
        return results

    domain_rules = rules[domain]

    subdomain_keys = []
    if subdomain:
        subdomain_keys.append(subdomain)
    if subdomain != "www":
        subdomain_keys.append("www")
    if subdomain != "":
        subdomain_keys.append("")
    subdomain_keys.append(".")

    for sub_key in subdomain_keys:
        if sub_key not in domain_rules:
            continue
        if sub_key == "_name":
            continue

        site_rules = domain_rules[sub_key]
        if not isinstance(site_rules, list):
            continue

        for rule in site_rules:
            if not isinstance(rule, dict):
                continue

            sources = rule.get("source", [])
            if not isinstance(sources, list):
                sources = [sources]

            for source in sources:
                params = _match_path(source, path)
                if params:
                    target = rule.get("target", "")
                    title = rule.get("title", "")

                    if isinstance(target, dict) and target.get("__type") == "function":
                        template = target.get("template", "")
                        target_url = _apply_target_template(template, params)
                    elif isinstance(target, str):
                        target_url = _apply_target_template(target, params)
                    else:
                        continue

                    target_url = target_url.replace("//", "/")

                    results.append({
                        "title": title,
                        "source": source,
                        "target": target_url,
                        "url": f"rsshub://{target_url.lstrip('/')}",
                        "full_url": f"http://localhost:1200/{target_url.lstrip('/')}"
                    })

    return results


def get_rsshub_url(route: str, rsshub_host: str = "http://localhost:1200") -> str:
    """Convert a rsshub:// route to full URL."""
    if route.startswith("rsshub://"):
        route = route[9:]
    return f"{rsshub_host.rstrip('/')}/{route.lstrip('/')}"


def parse_rsshub_url(url: str) -> Optional[Dict[str, str]]:
    """Parse a rsshub:// URL and extract route info."""
    if not url.startswith("rsshub://"):
        return None

    route = url[9:]
    parts = route.split("/")

    if len(parts) >= 3:
        name = f"{parts[0].capitalize()} {parts[2]}"
    else:
        name = route

    return {
        "route": route,
        "fullUrl": f"http://localhost:1200/{route}",
        "name": name
    }


if __name__ == "__main__":
    test_urls = [
        "https://x.com/elonmusk",
        "https://github.com/anthropics",
        "https://www.youtube.com/channel/UCzQcOxyG8x7oPGqSfOgaVgw",
        "https://36kr.com/newsflashes",
        "https://bilibili.com/user/672346917",
    ]

    print(f"Loaded {len(_load_rules())} domains from rules file")

    for url in test_urls:
        print(f"\n{url}")
        routes = discover_rsshub_routes(url)
        if routes:
            for r in routes:
                print(f"  -> {r['url']} ({r['title']})")
        else:
            print("  -> No routes found")
