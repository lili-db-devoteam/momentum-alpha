"""Audit-log als hashketen.

Elk ontvangstbewijs bevat de hash van het vorige. Wie achteraf één veld aanpast,
een bewijs weghaalt of de volgorde wijzigt, breekt de keten, en verify() wijst
aan waar. Beperking: het weglaten van het laatste bewijs is met een keten
alleen niet te zien. De hash is ongesleuteld: wie het hele log kan herschrijven, kan de
keten opnieuw berekenen; in productie moet het anker (de laatste hash) extern bewaard worden.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType

GENESIS = "0" * 64


def _digest(fields: Mapping[str, object], prev_hash: str) -> str:
    body = {**fields, "prev_hash": prev_hash}
    canonical = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Receipt:
    fields: Mapping[str, object]
    prev_hash: str
    hash: str


class AuditLog:
    def __init__(self, receipts: Iterable[Receipt] = ()) -> None:
        self._receipts: list[Receipt] = list(receipts)

    def __len__(self) -> int:
        return len(self._receipts)

    @property
    def receipts(self) -> tuple[Receipt, ...]:
        return tuple(self._receipts)

    def append(self, fields: Mapping[str, object], now: datetime | None = None) -> Receipt:
        body = json.loads(json.dumps(dict(fields), ensure_ascii=False))  # diepe kopie, en garandeert JSON
        body["tijd"] = (now or datetime.now(UTC)).isoformat(timespec="seconds")
        prev = self._receipts[-1].hash if self._receipts else GENESIS
        receipt = Receipt(MappingProxyType(body), prev, _digest(body, prev))
        self._receipts.append(receipt)
        return receipt

    def verify(self) -> tuple[bool, int | None]:
        prev = GENESIS
        for i, r in enumerate(self._receipts):
            if r.prev_hash != prev or _digest(r.fields, r.prev_hash) != r.hash:
                return False, i
            prev = r.hash
        return True, None

    def tampered_copy(self, index: int, field: str, value: object) -> AuditLog:
        """Kopie waarin één veld is aangepast zonder de hash te herberekenen (voor de demo)."""
        receipts = list(self._receipts)
        r = receipts[index]
        receipts[index] = Receipt(MappingProxyType({**r.fields, field: value}), r.prev_hash, r.hash)
        return AuditLog(receipts)

    def rows(self) -> list[dict]:
        return [{**r.fields, "prev_hash": r.prev_hash, "hash": r.hash} for r in self._receipts]
