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


class Contract(gl.Contract):
    records: TreeMap[str, FactRecord]
    next_id: bigint

    def __init__(self):
        self.next_id = bigint(0)

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
