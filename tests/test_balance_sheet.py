"""Tests for balance sheet generation."""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sie_parser.parser import parse_sie_file
from src.financial.balance_sheet import generate_balance_sheet

SIE_FILE = Path(__file__).parent.parent / "sieFiles" / "FrosteusConsultingAB20260420_125427.se"


def test_balance_sheet_cash():
    sie = parse_sie_file(SIE_FILE)
    bs = generate_balance_sheet(sie)

    # Kassa och bank should include 1930: 40610
    cash_line = [l for l in bs.assets if l.label == "Kassa och bank"]
    assert len(cash_line) == 1
    assert cash_line[0].amount == Decimal("40610")


def test_balance_sheet_equity():
    sie = parse_sie_file(SIE_FILE)
    bs = generate_balance_sheet(sie)

    # Aktiekapital = -(-25000) = 25000
    aktiekapital = [l for l in bs.equity_and_liabilities if l.label == "Aktiekapital"]
    assert len(aktiekapital) == 1
    assert aktiekapital[0].amount == Decimal("25000")


def test_balance_sheet_total_assets():
    sie = parse_sie_file(SIE_FILE)
    bs = generate_balance_sheet(sie)

    # Total assets = 40610 (kassa)
    assert bs.total_assets == Decimal("40610")


def test_balance_sheet_is_balanced():
    sie = parse_sie_file(SIE_FILE)
    bs = generate_balance_sheet(sie)

    # Total assets should equal total equity + liabilities
    # Assets: 40610
    # Equity: 25000 (aktiekapital) + 12036 (årets resultat) = 37036
    # Liabilities: 3574 (momsredovisningskonto 2650)
    # Total EK + skulder = 37036 + 3574 = 40610
    total_ek_skulder = [l for l in bs.equity_and_liabilities
                        if l.label == "SUMMA EGET KAPITAL OCH SKULDER"]
    assert len(total_ek_skulder) == 1
    # Assets = 40610, EK + skulder = 25000 + 12036 + 3574 = 40610
    assert total_ek_skulder[0].amount == Decimal("40610")
    assert total_ek_skulder[0].amount == bs.total_assets


def test_balance_sheet_liabilities():
    sie = parse_sie_file(SIE_FILE)
    bs = generate_balance_sheet(sie)

    # Momsredovisningskonto 2650: -3574 → shown as 3574 (positive liability)
    ovriga_skulder = [l for l in bs.equity_and_liabilities
                      if l.label == "Övriga kortfristiga skulder"]
    assert len(ovriga_skulder) == 1
    assert ovriga_skulder[0].amount == Decimal("3574")
