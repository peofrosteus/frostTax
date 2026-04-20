"""Tests for the SIE4 parser."""

import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sie_parser.parser import parse_sie_file
from src.sie_parser.models import SieFile

SIE_FILE = Path(__file__).parent.parent / "sieFiles" / "FrosteusConsultingAB20260420_125427.se"


def test_parse_metadata():
    sie = parse_sie_file(SIE_FILE)
    assert sie.flag == 0
    assert sie.format == "PC8"
    assert sie.sie_type == 4
    assert sie.program == "Fortnox"


def test_parse_company():
    sie = parse_sie_file(SIE_FILE)
    assert sie.company.name == "Frosteus Consulting AB"
    assert sie.company.org_number == "559532-5340"
    assert sie.company.address_contact == "Cecilia Frosteus"


def test_parse_fiscal_year():
    sie = parse_sie_file(SIE_FILE)
    assert sie.company.fiscal_year_start is not None
    assert sie.company.fiscal_year_start.year == 2025
    assert sie.company.fiscal_year_start.month == 1
    assert sie.company.fiscal_year_end is not None
    assert sie.company.fiscal_year_end.year == 2025
    assert sie.company.fiscal_year_end.month == 12


def test_parse_accounts():
    sie = parse_sie_file(SIE_FILE)
    # Should have parsed many accounts
    assert len(sie.accounts) > 100

    # Check a specific account
    assert "1930" in sie.accounts
    assert sie.accounts["1930"].name == "Företagskonto/checkkonto/affärskonto"

    # Check SRU code
    assert sie.accounts["1930"].sru_code == "7281"


def test_parse_balances():
    sie = parse_sie_file(SIE_FILE)

    # IB for 1930 should be 0
    assert sie.get_ib("1930", 0) == Decimal(0)

    # UB for 1930 should be 40610
    assert sie.get_ub("1930", 0) == Decimal(40610)

    # UB for 2081 (aktiekapital) should be -25000
    assert sie.get_ub("2081", 0) == Decimal(-25000)

    # UB for 2650 (momsredovisning)
    assert sie.get_ub("2650", 0) == Decimal(-3574)


def test_parse_result_rows():
    sie = parse_sie_file(SIE_FILE)

    # RES for 3001 (försäljning 25% moms) = -6720
    assert sie.get_result("3001", 0) == Decimal("-6720")

    # RES for 3010 (försäljning tjänster) = -7840
    assert sie.get_result("3010", 0) == Decimal("-7840")

    # RES for 6570 (bankkostnader) = 2500
    assert sie.get_result("6570", 0) == Decimal("2500")


def test_parse_vouchers():
    sie = parse_sie_file(SIE_FILE)

    # Should have parsed all vouchers
    assert len(sie.vouchers) > 0

    # Find voucher A1 (Aktiekapital)
    a1 = next(v for v in sie.vouchers if v.series == "A" and v.number == "1")
    assert a1.text == "Aktiekapital"
    assert len(a1.transactions) == 2
    assert a1.transactions[0].account == "2081"
    assert a1.transactions[0].amount == Decimal(-25000)
    assert a1.transactions[1].account == "1930"
    assert a1.transactions[1].amount == Decimal(25000)


def test_parse_dimensions():
    sie = parse_sie_file(SIE_FILE)
    assert len(sie.dimensions) == 2
    dim_names = [d.name for d in sie.dimensions]
    assert "Kostnadsställe" in dim_names
    assert "Projekt" in dim_names


def test_parse_period_balances():
    sie = parse_sie_file(SIE_FILE)
    assert len(sie.psaldo) > 0

    # Check a specific period balance
    oct_1930 = [p for p in sie.psaldo if p.period == "202510" and p.account == "1930"]
    assert len(oct_1930) == 1
    assert oct_1930[0].amount == Decimal("3494")


def test_accounts_in_range():
    sie = parse_sie_file(SIE_FILE)
    revenue_accounts = sie.accounts_in_range(3000, 3099)
    account_numbers = [a.number for a in revenue_accounts]
    assert "3000" in account_numbers
    assert "3001" in account_numbers
    assert "3010" in account_numbers


def test_sum_result_range():
    sie = parse_sie_file(SIE_FILE)
    # Sum all revenue (3000-3999): should be negative (credit)
    total_revenue = sie.sum_result_range(3000, 3999)
    # 3001: -6720 + 3010: -7840 + 3740: 0.15 + 3999: -0.65 = -14560.50
    assert total_revenue == Decimal("-6720") + Decimal("-7840") + Decimal("0.15") + Decimal("-0.65")
