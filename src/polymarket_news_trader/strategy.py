from __future__ import annotations

from dataclasses import dataclass
import re

from .news import NewsItem


@dataclass(frozen=True)
class Action:
    rule_name: str
    token_id: str
    outcome: str
    kind: str  # market | limit
    side: str  # buy | sell
    size_usdc: float | None
    price: float | None
    size_shares: float | None
    max_price: float | None


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokenize(text: str) -> set[str]:
    if not text:
        return set()
    return set(text.split())


def _expand_keywords(keywords: list[str], synonyms: dict[str, list[str]]) -> list[str]:
    out: list[str] = []
    for k in keywords:
        if not k:
            continue
        k_norm = k.lower()
        out.append(k)
        syns = synonyms.get(k_norm) or []
        for s in syns:
            if s and s not in out:
                out.append(s)
    return out


def _contains_all(norm_text: str, tokens: set[str], keywords: list[str]) -> bool:
    for k in keywords:
        if not k:
            continue
        if " " in k:
            if k.lower() not in norm_text:
                return False
        else:
            if k.lower() not in tokens:
                return False
    return True


def _contains_any(norm_text: str, tokens: set[str], keywords: list[str]) -> bool:
    if not keywords:
        return True
    for k in keywords:
        if not k:
            continue
        if " " in k:
            if k.lower() in norm_text:
                return True
        else:
            if k.lower() in tokens:
                return True
    return False


def _contains_none(norm_text: str, tokens: set[str], keywords: list[str]) -> bool:
    for k in keywords:
        if not k:
            continue
        if " " in k:
            if k.lower() in norm_text:
                return False
        else:
            if k.lower() in tokens:
                return False
    return True


def _matches_patterns(text: str, patterns: list[str]) -> bool:
    if not patterns:
        return True
    for p in patterns:
        try:
            if re.search(p, text, flags=re.IGNORECASE):
                return True
        except re.error:
            continue
    return False


def _score_terms(norm_text: str, tokens: set[str], terms: list[str]) -> int:
    score = 0
    for t in terms:
        if not t:
            continue
        if " " in t:
            if t.lower() in norm_text:
                score += 1
        else:
            if t.lower() in tokens:
                score += 1
    return score


def match_rules(
    *,
    item: NewsItem,
    rules: list[dict],
    now: float,
    last_rule_fired_at: dict[str, float],
) -> list[dict]:
    raw_text = item.title + "\n" + item.summary
    norm_text = _normalize(raw_text)
    tokens = _tokenize(norm_text)

    matched: list[dict] = []
    for rule in rules:
        name = str(rule.get("name") or "")
        if not name:
            continue

        categories = [str(c).lower() for c in (rule.get("categories") or [])]
        if categories and item.category.lower() not in categories:
            continue

        cooldown_minutes = float(rule.get("cooldown_minutes") or 0)
        last = float(last_rule_fired_at.get(name) or 0)
        if cooldown_minutes > 0 and (now - last) < cooldown_minutes * 60:
            continue

        synonyms_raw = rule.get("synonyms") or {}
        synonyms: dict[str, list[str]] = {}
        if isinstance(synonyms_raw, dict):
            for k, v in synonyms_raw.items():
                if not k:
                    continue
                if isinstance(v, list):
                    synonyms[str(k).lower()] = [str(x).lower() for x in v if x]

        all_kw = _expand_keywords(list(rule.get("all") or []), synonyms)
        any_kw = _expand_keywords(list(rule.get("any") or []), synonyms)
        not_kw = _expand_keywords(list(rule.get("not") or []), synonyms)

        if not _contains_all(norm_text, tokens, all_kw):
            continue
        if not _contains_any(norm_text, tokens, any_kw):
            continue
        if not _contains_none(norm_text, tokens, not_kw):
            continue

        patterns = list(rule.get("patterns") or [])
        if not _matches_patterns(raw_text, patterns):
            continue

        score_terms = list(rule.get("score") or [])
        min_score = int(rule.get("min_score") or 0)
        if min_score > 0:
            if _score_terms(norm_text, tokens, score_terms) < min_score:
                continue

        matched.append(rule)

    return matched


def build_action(rule_name: str, token_id: str, outcome: str, order: dict) -> Action:
    kind = str(order.get("kind") or "market").lower()
    side = str(order.get("side") or "buy").lower()

    if kind not in {"market", "limit"}:
        raise ValueError(f"Unsupported order.kind: {kind}")
    if side not in {"buy", "sell"}:
        raise ValueError(f"Unsupported order.side: {side}")

    size_usdc = order.get("size_usdc")
    size_shares = order.get("size_shares")
    price = order.get("price")
    max_price = order.get("max_price")

    return Action(
        rule_name=rule_name,
        token_id=token_id,
        outcome=outcome,
        kind=kind,
        side=side,
        size_usdc=float(size_usdc) if size_usdc is not None else None,
        price=float(price) if price is not None else None,
        size_shares=float(size_shares) if size_shares is not None else None,
        max_price=float(max_price) if max_price is not None else None,
    )
