#!/usr/bin/env python3
"""Minimal listing_compliance_check rule engine (v0.1)."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RULES_DIR = Path(__file__).resolve().parent

# Keyword patterns keyed by rule code. severity comes from rules JSON.
# Match is case-insensitive; Chinese matched as literal substrings.
PATTERNS: dict[str, list[str]] = {
    # HKTVmall
    "HKTV_MED_CLAIM": [
        r"治(?:療|癒|好)?",
        r"根治",
        r"藥效",
        r"醫療級",
        r"絕無副作用",
        r"無副作用",
        r"益精",
        r"腎虛",
        r"壯陽",
        r"藥用",
        r"處方",
        r"cure",
        r"treat(?:ment|s)?",
    ],
    "HKTV_EXAGGERATE": [
        r"全港最",
        r"香港第一",
        r"保證",
        r"聖品",
        r"頂級(?!黑瑪卡)",  # allow brand-ish; still catch 頂級 alone in claims
        r"第一(?:名|品牌)?",
        r"絕對有效",
        r"100%有效",
        r"掌握伴侶",
        r"高峰狀態",
    ],
    "HKTV_COUNTERFEIT": [
        r"正品保證",
        r"正版保證",
        r"絕對正品",
        r"防偽保證",
    ],
    "HKTV_RESTRICTED": [
        r"香煙|香菸|雪茄",
        r"手槍|槍械|彈藥",
        r"處方藥",
        r"成人用品|情趣用品",
    ],
    "HKTV_PARALLEL_LABEL": [
        r"香港行貨",
        r"行貨",
    ],
    "HKTV_PRICE_BAIT": [
        r"限時(?!優惠結束)",
        r"史上最低",
        r"史低",
    ],
    "HKTV_CONTACT_OFF": [
        r"whatsapp|WhatsApp|WA\s*：|加我微信|私訊付款|銀行轉帳下單",
    ],
    "HKTV_LANG_MIX": [
        r"[\u4e00-\u9fff].*[\u7b80].*",  # weak; skip heavy use
    ],
    "HKTV_STOCK_FAKE": [
        r"僅餘\s*1\s*件",
        r"只剩\s*1\s*件",
        r"最後一件",
    ],
    "HKTV_IP_LOGO": [
        r"奧運|Olympic",
        r"HKTVmall\s*官方",
    ],
    # Shopee MY
    "SPMY_MED_CLAIM": [
        r"cure",
        r"treat(?:ment|s)?",
        r"\bFDA\b",
        r"醫療",
        r"根治",
        r"藥效",
        r"no side effects?",
        r"絕無副作用",
    ],
    "SPMY_HALAL_FALSE": [
        r"\bhalal\b",
        r"清真",
    ],
    "SPMY_PROHIBITED": [
        r"cigarette|tobacco|vape",
        r"prescription\s*drug",
        r"weapon|firearm",
        r"adult\s*toy",
    ],
    "SPMY_IP_BRAND": [
        r"\bauthentic\b",
        r"100%\s*original",
        r"正品保證",
    ],
    "SPMY_TITLE_KEYWORD": [
        r"[A-Z]{8,}",
        r"!{3,}",
    ],
    "SPMY_PRICE_MANIP": [
        r"biggest\s*sale",
        r"lowest\s*price\s*ever",
        r"史上最低",
    ],
    "SPMY_LOCAL_FALSE": [
        r"ready\s*stock\s*my",
        r"local\s*stock",
        r"kl\s*stock",
    ],
    "SPMY_WARRANTY_VAGUE": [
        r"lifetime\s*warranty",
        r"終身保固|終身保養",
    ],
    "SPMY_PDPA_PII": [
        r"01[0-9]-?[0-9]{7,8}",
        r"\b\d{12,}\b",
    ],
    "SPMY_CURRENCY_MIX": [
        r"\bHKD\b|\bHK\$",
        r"\bSGD\b|\bS\$",
    ],
    "SPMY_STAR_FAKE": [
        r"5\s*star.*voucher",
        r"好評.*回贈",
        r"給五星",
        r"leave\s*5\s*star",
    ],
}

# Codes that need context checks beyond keywords
CONTEXT_CHECKS = {
    "HKTV_PARALLEL_LABEL": "origin_mismatch",
}


def load_rules(platform: str) -> dict:
    path = RULES_DIR / f"rules_{platform}.json"
    if not path.exists():
        # allow hktvmall / shopee_my filenames
        alt = {
            "hktvmall": "rules_hktvmall.json",
            "shopee_my": "rules_shopee_my.json",
        }.get(platform)
        if alt:
            path = RULES_DIR / alt
    if not path.exists():
        raise FileNotFoundError(f"No rules for platform={platform}: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def find_matches(text: str, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    for p in patterns:
        try:
            m = re.search(p, text, flags=re.IGNORECASE)
        except re.error:
            continue
        if m:
            hits.append(m.group(0))
    return hits


def origin_mismatch(title: str, description: str, claims: str) -> bool:
    blob = f"{title}\n{description}\n{claims}"
    has_hk_origin = bool(re.search(r"產地\s*[:：]?\s*香港|香港行貨", blob))
    has_foreign = bool(
        re.search(r"生產地\s*[:：]?\s*(?!香港)[\u4e00-\u9fffA-Za-z]+|Made in (?!Hong Kong)", blob, re.I)
    )
    return has_hk_origin and has_foreign


def check(
    platform: str,
    title: str = "",
    description: str = "",
    category: str = "",
    claims: str = "",
    language: str = "zh-Hant-HK",
) -> dict:
    rules_doc = load_rules(platform)
    rules = {r["code"]: r for r in rules_doc["rules"]}
    blob = "\n".join([title, description, category, claims])
    issues: list[dict] = []

    for code, rule in rules.items():
        patterns = PATTERNS.get(code, [])
        hits = find_matches(blob, patterns) if patterns else []

        # Context: parallel label only if origin mismatch OR hit without clarification
        if code == "HKTV_PARALLEL_LABEL":
            if origin_mismatch(title, description, claims):
                issues.append(
                    {
                        "code": code,
                        "severity": rule["severity"],
                        "where": "產地／生產地／標題",
                        "why": rule["trigger"] + "（偵測到產地與生產地不一致）",
                        "fix": rule["fix"],
                        "matched": hits or ["origin_mismatch"],
                    }
                )
            continue

        # Halal: flag claim without certificate keyword nearby (simple heuristic)
        if code == "SPMY_HALAL_FALSE" and hits:
            if not re.search(r"JAKIM|證書|certificate", blob, re.I):
                issues.append(
                    {
                        "code": code,
                        "severity": rule["severity"],
                        "where": "title/description",
                        "why": rule["trigger"],
                        "fix": rule["fix"],
                        "matched": hits,
                    }
                )
            continue

        if hits:
            issues.append(
                {
                    "code": code,
                    "severity": rule["severity"],
                    "where": "title/description",
                    "why": rule["trigger"],
                    "fix": rule["fix"],
                    "matched": hits,
                }
            )

    has_block = any(i["severity"] == "block" for i in issues)
    has_revise = any(i["severity"] == "revise" for i in issues)
    if has_block:
        verdict = "block" if len([i for i in issues if i["severity"] == "block"]) >= 2 else "revise"
        # single block claim still revise for health soft claims; hard restricted = block
        hard = {"HKTV_RESTRICTED", "HKTV_COUNTERFEIT", "HKTV_WEIGHT_FALSE", "HKTV_PRICE_BAIT", "HKTV_IP_LOGO",
                "SPMY_PROHIBITED", "SPMY_IP_BRAND", "SPMY_PRICE_MANIP", "SPMY_STAR_FAKE"}
        if any(i["code"] in hard for i in issues):
            verdict = "block"
        else:
            verdict = "revise"
    elif has_revise:
        verdict = "revise"
    else:
        verdict = "pass"

    # risk score
    score = 0
    for i in issues:
        score += 35 if i["severity"] == "block" else 15
    score = min(100, score)

    return {
        "verdict": verdict,
        "risk_score": score,
        "safe_to_publish": verdict == "pass",
        "issues": [
            {k: v for k, v in i.items() if k != "matched"} | {"matched": i.get("matched", [])}
            for i in issues
        ],
        "notes": _notes(verdict, issues),
        "meta": {"platform": platform, "language": language, "engine": "v0.1"},
    }


def _notes(verdict: str, issues: list[dict]) -> str:
    if verdict == "pass":
        return "未觸發現有規則；仍建議人工抽查。"
    codes = ", ".join(i["code"] for i in issues)
    return f"觸發 {len(issues)} 條：{codes}。"


def main() -> None:
    p = argparse.ArgumentParser(description="listing_compliance_check")
    p.add_argument("--platform", required=True, choices=["hktvmall", "shopee_my"])
    p.add_argument("--title", default="")
    p.add_argument("--description", default="")
    p.add_argument("--category", default="")
    p.add_argument("--claims", default="")
    p.add_argument("--file", help="JSON file with title/description/...")
    p.add_argument("--language", default="zh-Hant-HK")
    args = p.parse_args()

    if args.file:
        data = json.loads(Path(args.file).read_text(encoding="utf-8"))
        result = check(
            platform=data.get("platform", args.platform),
            title=data.get("title", ""),
            description=data.get("description", ""),
            category=data.get("category", ""),
            claims=data.get("claims", ""),
            language=data.get("language", args.language),
        )
    else:
        result = check(
            platform=args.platform,
            title=args.title,
            description=args.description,
            category=args.category,
            claims=args.claims,
            language=args.language,
        )
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
