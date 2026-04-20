"""Tests for INK2 page 1 (correct field labels matching SKV blankett)."""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sie_parser.parser import parse_sie_file
from src.tax.ink2_tax_calc import calculate_ink2_tax

SIE_FILE = Path(__file__).parent.parent / "sieFiles" / "FrosteusConsultingAB20260420_125427.se"


def test_field_1_1_is_overskott():
    """1.1 should be 'Överskott av näringsverksamhet', not 'Bokfört resultat'."""
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    f11 = calc.get_field("1.1")
    assert "Överskott" in f11.label
    assert f11.amount == Decimal("12036")


def test_field_1_2_is_underskott():
    """1.2 holds underskott (0 in this case)."""
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    assert calc.get_field("1.2").amount == Decimal(0)
    assert "Underskott" in calc.get_field("1.2").label


def test_field_1_4_is_slp():
    """1.4 should be SLP underlag, not 'skattemässigt resultat'."""
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    f14 = calc.get_field("1.4")
    assert "löneskatt" in f14.label.lower()


def test_no_fastighetsavgift():
    """Frosteus Consulting has no fastigheter, so 1.8–1.15 should be 0."""
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    for fid in ["1.8", "1.9", "1.10", "1.11", "1.12", "1.13", "1.14", "1.15"]:
        assert calc.get_field(fid).amount == Decimal(0)


def test_overskott_matches_ink2s():
    """1.1 should equal INK2S 4.15."""
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)

    from src.tax.ink2s_calc import calculate_ink2s
    ink2s = calculate_ink2s(sie)

    assert calc.get_field("1.1").amount == ink2s.get_field("4.15").amount


def test_all_fields_present():
    """All 18 fields on page 1 should be present."""
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    field_ids = [f.field_id for f in calc.fields]
    expected = [
        "1.1", "1.2", "1.3", "1.4", "1.5",
        "1.6a", "1.6b", "1.7a", "1.7b",
        "1.8", "1.9", "1.10", "1.11", "1.12",
        "1.13", "1.14", "1.15", "1.16", "1.17",
    ]
    for fid in expected:
        assert fid in field_ids, f"Field {fid} missing"
