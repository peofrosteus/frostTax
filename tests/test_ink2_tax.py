"""Tests for INK2 tax calculation."""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sie_parser.parser import parse_sie_file
from src.tax.ink2_tax_calc import calculate_ink2_tax, CORPORATE_TAX_RATE

SIE_FILE = Path(__file__).parent.parent / "sieFiles" / "FrosteusConsultingAB20260420_125427.se"


def test_bokfort_resultat():
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    # Bokfört resultat = resultat före skatt = 12036
    assert calc.get_field("1.1").amount == Decimal("12036")


def test_ej_avdragsgilla_zero_for_this_file():
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    # No non-deductible costs booked in this SIE file
    assert calc.get_field("1.2").amount == Decimal(0)


def test_ej_skattepliktiga_zero_for_this_file():
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    # No tax-free income in this SIE file
    assert calc.get_field("1.3").amount == Decimal(0)


def test_resultat_fore_dispositioner():
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    # 1.4 = 1.1 + 1.2 - 1.3 = 12036 + 0 - 0 = 12036
    assert calc.get_field("1.4").amount == Decimal("12036")


def test_no_periodiseringsfond():
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    # No periodiseringsfond activity
    assert calc.get_field("1.5").amount == Decimal(0)
    assert calc.get_field("1.6").amount == Decimal(0)
    assert calc.get_field("1.7").amount == Decimal(0)


def test_overskott_naringsverksamhet():
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    # Same as bokfört resultat since no adjustments
    assert calc.get_field("1.11").amount == Decimal("12036")


def test_skattemassigt_resultat():
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    assert calc.get_field("1.13").amount == Decimal("12036")


def test_bolagsskatt():
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    # 12036 * 20.6% = 2479.416 → rounded to 2479
    expected_tax = Decimal("2479")
    assert calc.get_field("1.14").amount == expected_tax


def test_skatt_att_betala():
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    # Same as bolagsskatt since no foreign tax credit
    assert calc.get_field("1.16").amount == calc.get_field("1.14").amount


def test_all_16_fields_present():
    sie = parse_sie_file(SIE_FILE)
    calc = calculate_ink2_tax(sie)
    field_ids = [f.field_id for f in calc.fields]
    for i in range(1, 17):
        assert f"1.{i}" in field_ids, f"Field 1.{i} missing"
