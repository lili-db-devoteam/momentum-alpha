from datetime import UTC, datetime

import pytest

from engine.audit import GENESIS, AuditLog

T0 = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def make_log(n=4):
    log = AuditLog()
    for i in range(n):
        log.append({"actie": f"A{i}", "omschrijving": f"€{i}.000", "regel": i, "mandaat": {"vraag_boven": 500}}, now=T0)
    return log


def test_empty_log_verifies():
    assert AuditLog().verify() == (True, None)


def test_chain_links_and_full_hashes():
    r = make_log().receipts
    assert r[0].prev_hash == GENESIS
    assert all(r[i].prev_hash == r[i - 1].hash for i in range(1, len(r)))
    assert all(len(x.hash) == 64 for x in r)
    assert make_log().verify() == (True, None)


def test_timestamp_is_iso_utc():
    assert make_log(1).receipts[0].fields["tijd"] == "2026-09-30T12:00:00+00:00"


def test_hash_is_deterministic():
    assert make_log().receipts[-1].hash == make_log().receipts[-1].hash


@pytest.mark.parametrize("i", range(4))
def test_changed_field_detected_at_that_receipt(i):
    assert make_log().tampered_copy(i, "omschrijving", "x").verify() == (False, i)


def test_changed_timestamp_detected():
    assert make_log().tampered_copy(1, "tijd", "2020-01-01T00:00:00+00:00").verify() == (False, 1)


def test_removed_middle_receipt_detected():
    r = make_log().receipts
    assert AuditLog([r[0], r[2], r[3]]).verify() == (False, 1)


def test_reordered_receipts_detected():
    r = make_log().receipts
    assert AuditLog([r[0], r[2], r[1], r[3]]).verify() == (False, 1)


def test_tampered_copy_leaves_original_intact():
    log = make_log()
    log.tampered_copy(2, "omschrijving", "x")
    assert log.verify() == (True, None)
    assert log.receipts[2].fields["omschrijving"] == "€2.000"


def test_append_detaches_from_caller_dict():
    log = AuditLog()
    fields = {"a": 1, "nested": {"b": 2}}
    log.append(fields, now=T0)
    fields["a"] = 99
    fields["nested"]["b"] = 99
    assert log.verify() == (True, None)


def test_receipt_fields_are_read_only():
    r = make_log(1).receipts[0]
    with pytest.raises(TypeError):
        r.fields["actie"] = "Z"


def test_non_ascii_fields_verify():
    log = AuditLog()
    log.append({"omschrijving": "Café · €2.400 — 's nachts"}, now=T0)
    assert log.verify() == (True, None)


def test_rows_include_hashes():
    row = make_log(1).rows()[0]
    assert row["prev_hash"] == GENESIS
    assert len(row["hash"]) == 64
    assert row["actie"] == "A0"
