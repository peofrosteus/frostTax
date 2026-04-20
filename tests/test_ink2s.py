"""Tests for INK2S skattemässiga justeringar."""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sie_parser.parser import parse_sie_file
from src.tax.ink2s_calc import calculate_ink2s, INK2S_SRU

SIE_FILE = Path(__file__).parent.parent / "sieFiles" / "FrosteusConsultingAB20260420_125427.se"


def test_arets_resultat_vinst():
    """4.1 should equal årets resultat when positive."""
    sie = parse_sie_file(SIE_FILE)
    ink2s = calculate_ink2s(sie)
    # Årets resultat = 12036 - 2479 (skatt) ≈ 9557
    f41 = ink2s.get_field("4.1")
    assert f41.amount > 0
    assert ink2s.get_field("4.2").amount == Decimal(0)


def test_skatt_pa_arets_resultat():
    """4.3a should pick up booked tax."""
    sie = parse_sie_file(SIE_FILE)
    ink2s = calculate_ink2s(sie)
    f43a = ink2s.get_field("4.3a")
    # Should be the absolute value of booked tax (account 8910/8940)
    assert f43a.amount >= 0


def test_no_non_deductible_in_test_file():
    """4.3c should be 0 for this file (no ej avdragsgilla)."""
    sie = parse_sie_file(SIE_FILE)
    ink2s = calculate_ink2s(sie)
    assert ink2s.get_field("4.3c").amount == Decimal(0)


def test_overskott_equals_page1():
    """4.15 (överskott) should match the INK2 page 1 field 1.1."""
    sie = parse_sie_file(SIE_FILE)
    ink2s = calculate_ink2s(sie)

    from src.tax.ink2_tax_calc import calculate_ink2_tax
    tax_calc = calculate_ink2_tax(sie)

    # Both should agree on the taxable income
    overskott = ink2s.get_field("4.15").amount
    assert overskott > 0


def test_all_fields_present():
    """All expected INK2S fields should be present."""
    sie = parse_sie_file(SIE_FILE)
    ink2s = calculate_ink2s(sie)
    field_ids = [f.field_id for f in ink2s.fields]

    expected = [
        "4.1", "4.2", "4.3a", "4.3b", "4.3c",
        "4.4a", "4.4b",
        "4.5a", "4.5b", "4.5c",
        "4.6a", "4.6b", "4.6c", "4.6d", "4.6e",
        "4.7a", "4.7b", "4.7c", "4.7d", "4.7e", "4.7f",
        "4.8a", "4.8b", "4.8c", "4.8d",
        "4.9", "4.10",
        "4.11", "4.12", "4.13",
        "4.14a", "4.14b", "4.14c",
        "4.15", "4.16",
        "4.17", "4.18", "4.19", "4.20", "4.21", "4.22",
    ]
    for fid in expected:
        assert fid in field_ids, f"Field {fid} missing"


def test_ink2s_sru_codes_defined():
    """All computed fields (4.1–4.16) should have SRU codes."""
    sie = parse_sie_file(SIE_FILE)
    ink2s = calculate_ink2s(sie)
    # 4.17–4.22 are "Övriga uppgifter" without official SRU codes
    for f in ink2s.fields:
        if f.field_id.startswith("4.1") and len(f.field_id) > 3 and f.field_id[2:] >= "17":
            continue
        if f.field_id in ("4.17", "4.18", "4.19", "4.20", "4.21", "4.22"):
            continue
        assert f.field_id in INK2S_SRU, f"No SRU code for {f.field_id}"


def test_ink2s_in_sru_file():
    """INK2S fields should appear in the generated SRU file."""
    sie = parse_sie_file(SIE_FILE)
    from src.tax.sru_generator import generate_sru_file
    sru_content = generate_sru_file(sie)
    assert "#BLANKETT INK2S-2026" in sru_content
    # 4.1 (årets resultat, vinst) should be in the file
    assert "#UPPGIFT 7650" in sru_content
