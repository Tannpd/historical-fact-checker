# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *

import json
import typing
from dataclasses import dataclass


@allow_storage
@dataclass
class FactRecord:
    claim: str
    url1: str
    url2: str
    verdict: str  # TRUE | FALSE | UNVERIFIABLE
    confidence: bigint
    reason: str


def _normalize_verdict(verdict: str) -> str:
    v = str(verdict or "").strip().upper()
    if "TRUE" in v:
        return "TRUE"
    if "FALSE" in v:
        return "FALSE"
    if "UNVERIFIABLE" in v or "UNVERIFY" in v or "UNKNOWN" in v:
        return "UNVERIFIABLE"
    return "UNVERIFIABLE"


def _normalize_confidence(conf_val: typing.Any) -> int:
    try:
        c = int(conf_val)
    except Exception:
        c = 0
    return max(0, min(100, c))


def _validate_url(url: str) -> bool:
    if not url:
        return False
    u = url.strip().lower()
    return u.startswith("http://") or u.startswith("https://")


class Contract(gl.Contract):
    records: TreeMap[str, FactRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

    @gl.public.write
    def verify_claim(self, claim: str, url1: str, url2: str) -> None:
        if not claim or not claim.strip():
            raise gl.vm.UserError("claim must not be empty")
        if not _validate_url(url1):
            raise gl.vm.UserError("url1 must be a valid HTTP/HTTPS URL")
        if not _validate_url(url2):
            raise gl.vm.UserError("url2 must be a valid HTTP/HTTPS URL")

        claim_clean = claim.strip()
        u1 = url1.strip()
        u2 = url2.strip()

        def leader_fn() -> str:
            # Live web rendering with text mode
            try:
                page1 = gl.nondet.web.render(u1, mode="text")
            except Exception:
                page1 = "Error: Could not retrieve URL 1 content."

            try:
                page2 = gl.nondet.web.render(u2, mode="text")
            except Exception:
                page2 = "Error: Could not retrieve URL 2 content."

            # Truncate page text to fit prompt context
            text1_truncated = str(page1)[:3000]
            text2_truncated = str(page2)[:3000]

            prompt = f"""You are a strict historical fact-checker for educational and digital curriculum materials.
Cross-reference the provided claim against the retrieved text from the two reference URLs.

CLAIM TO VERIFY:
---
{claim_clean}
---

RETRIEVED TEXT FROM URL 1 ({u1}):
---
{text1_truncated}
---

RETRIEVED TEXT FROM URL 2 ({u2}):
---
{text2_truncated}
---

Rules for fact-checking evaluation:
- Assign "TRUE" if the reference texts explicitly confirm or support the factual claim.
- Assign "FALSE" if the reference texts explicitly contradict or refute the claim (e.g. historical dates or events do not match).
- Assign "UNVERIFIABLE" if the reference texts do not contain enough relevant information to prove or disprove the claim, or if the page retrievals failed.
- Assign a confidence score from 0 to 100 representing how confident you are in this verification.
- Provide a brief explanation reason (maximum 200 characters) detailing the cross-referencing findings.

Respond ONLY with a valid JSON object matching the following structure:
{{
  "verdict": "TRUE" | "FALSE" | "UNVERIFIABLE",
  "confidence": <integer 0-100>,
  "reason": "explanation string"
}}"""
            res = gl.nondet.exec_prompt(prompt, response_format="json")
            if not isinstance(res, dict):
                res = {}

            verdict = _normalize_verdict(res.get("verdict", "UNVERIFIABLE"))
            confidence = _normalize_confidence(res.get("confidence", 0))
            reason = str(res.get("reason", "")).strip()[:200]
            if not reason:
                reason = "No explanation provided."

            return json.dumps({
                "verdict": verdict,
                "confidence": confidence,
                "reason": reason
            }, sort_keys=True)

        def validator_fn(leader_res: typing.Any) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            try:
                leader_data = json.loads(leader_res.calldata)
            except Exception:
                return False

            leader_verdict = _normalize_verdict(leader_data.get("verdict"))
            leader_confidence = _normalize_confidence(leader_data.get("confidence"))

            try:
                mine_json = leader_fn()
                mine_data = json.loads(mine_json)
            except Exception:
                return False

            mine_verdict = _normalize_verdict(mine_data.get("verdict"))
            mine_confidence = _normalize_confidence(mine_data.get("confidence"))

            if leader_verdict != mine_verdict:
                return False

            if abs(leader_confidence - mine_confidence) > 20:
                return False

            return True

        raw_result = gl.vm.run_nondet_unsafe(leader_fn, validator_fn)
        payload = json.loads(raw_result)

        rid = str(self.next_id)
        self.records[rid] = FactRecord(
            claim=claim_clean,
            url1=u1,
            url2=u2,
            verdict=_normalize_verdict(payload.get("verdict")),
            confidence=bigint(_normalize_confidence(payload.get("confidence"))),
            reason=str(payload.get("reason")).strip()[:200]
        )
        self.next_id = self.next_id + bigint(1)

    @gl.public.view
    def get_record(self, record_id: str) -> str:
        if record_id not in self.records:
            raise gl.vm.UserError("Fact record not found")
        
        record = self.records[record_id]
        return json.dumps({
            "id": record_id,
            "claim": record.claim,
            "url1": record.url1,
            "url2": record.url2,
            "verdict": record.verdict,
            "confidence": int(record.confidence),
            "reason": record.reason
        })

    @gl.public.view
    def get_total_records(self) -> int:
        return int(self.next_id)
