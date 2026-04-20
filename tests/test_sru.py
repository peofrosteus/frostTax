"""Tests for SRU mapping and file generation."""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sie_parser.parser import parse_sie_file
from src.tax.sru_mapping import aggregate_sru
from src.tax.sru_generator import generate_sru_file

SIE_FILE = Path(__file__).parent.parent / "sieFiles" / "FrosteusConsultingAB20260420_125427.se"


def test_sru_aggregation():
    sie = parse_sie_file(SIE_FILE)
    fields = aggregate_sru(sie)

    # Should have aggregated fields
    assert len(fields) > 0

    # Check that SRU 7281 (kassa och bank) = 40610
    kassa = [f for f in fields if f.sru_code == "7281"]
    assert len(kassa) == 1
    assert kassa[0].amount == Decimal("40610")


def test_sru_revenue_mapping():
    sie = parse_sie_file(SIE_FILE)
    fields = aggregate_sru(sie)

    # SRU 7410 (nettoomsättning): 3001:-6720 + 3010:-7840 + 3740:0.15 = -14559.85
    revenue = [f for f in fields if f.sru_code == "7410"]
    assert len(revenue) == 1
    # Revenue accounts are negative (credit), SRU should show the raw value
    assert revenue[0].amount == Decimal("-6720") + Decimal("-7840") + Decimal("0.15")


def test_sru_field_numbers_correct():
    """Verify SRU fields have correct INK2R field numbers."""
    sie = parse_sie_file(SIE_FILE)
    fields = aggregate_sru(sie)

    # SRU 7281 should map to field 2.26 (Kassa och bank), not 2.16
    kassa = [f for f in fields if f.sru_code == "7281"]
    assert kassa[0].ink2_field == "2.26"

    # SRU 7410 should map to field 3.1 (Nettoomsättning), not 2.33
    revenue = [f for f in fields if f.sru_code == "7410"]
    assert revenue[0].ink2_field == "3.1"

    # SRU 7513 should map to field 3.7 (Övriga externa kostnader)
    ext_costs = [f for f in fields if f.sru_code == "7513"]
    if ext_costs:
        assert ext_costs[0].ink2_field == "3.7"


def test_sru_file_generation():
    sie = parse_sie_file(SIE_FILE)
    sru_content = generate_sru_file(sie)

    # Check SRU file structure
    assert "#DATABESKRIVNING_START" in sru_content
    assert "#DATABESKRIVNING_SLUT" in sru_content
    assert "#FIL_SLUT" in sru_content

    # All three blanketter should be present
    assert "#BLANKETT INK2-2026" in sru_content
    assert "#BLANKETT INK2R-2026" in sru_content
    assert "#BLANKETT INK2S-2026" in sru_content

    # Three BLANKETTSLUT (one per blankett)
    assert sru_content.count("#BLANKETTSLUT") == 3

    # Check org number
    assert "5595325340" in sru_content

    # Check company name
    assert "Frosteus Consulting AB" in sru_content


def test_sru_file_contains_fields():
    sie = parse_sie_file(SIE_FILE)
    sru_content = generate_sru_file(sie)

    # Should contain SRU code 7281 (kassa)
    assert "#UPPGIFT 7281 40610" in sru_content

    # Should contain fiscal year dates
    assert "#UPPGIFT 7012 20250101" in sru_content
    assert "#UPPGIFT 7013 20251231" in sru_content
