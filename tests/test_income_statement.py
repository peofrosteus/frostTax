"""Tests for income statement generation."""

import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sie_parser.parser import parse_sie_file
from src.financial.income_statement import generate_income_statement

SIE_FILE = Path(__file__).parent.parent / "sieFiles" / "FrosteusConsultingAB20260420_125427.se"


def test_income_statement_net_revenue():
    sie = parse_sie_file(SIE_FILE)
    stmt = generate_income_statement(sie)

    # Nettoomsättning = -(3001:-6720 + 3010:-7840 + 3740:0.15) = 14559.85
    # 3001, 3010, 3740 are in range 3000-3799
    assert stmt.net_revenue == Decimal("14559.85")


def test_income_statement_other_revenue():
    sie = parse_sie_file(SIE_FILE)
    stmt = generate_income_statement(sie)

    # Övriga rörelseintäkter = -(3999: -0.65 + 3740: 0.15) = 0.50
    # (3740 is in 3000-3699 range, so only 3999 goes to övriga)
    # Actually 3740 is 3740 which is in 3000-3699 → nettoomsättning
    # 3999 is in 3900-3999 → övriga rörelseintäkter
    # Let me check: The övriga rörelseintäkter line should pick up 3999
    ovriga_line = [l for l in stmt.lines if l.label == "Övriga rörelseintäkter"]
    assert len(ovriga_line) == 1
    assert ovriga_line[0].amount == Decimal("0.65")


def test_income_statement_external_costs():
    sie = parse_sie_file(SIE_FILE)
    stmt = generate_income_statement(sie)

    # Övriga externa kostnader (5000-6999):
    # 6060: 24.5 + 6570: 2500 = 2524.5
    ovriga_ext = [l for l in stmt.lines if l.label == "Övriga externa kostnader"]
    assert len(ovriga_ext) == 1
    assert ovriga_ext[0].amount == Decimal("-2524.5")


def test_income_statement_annual_result():
    sie = parse_sie_file(SIE_FILE)
    stmt = generate_income_statement(sie)

    # Årets resultat = nettoomsättning + övriga intäkter - kostnader
    # Nettoomsättning (3000-3799) = -((-6720) + (-7840) + 0.15) = 14559.85
    # Övriga rörelseintäkter (3900-3999) = -(-0.65) = 0.65
    # Övriga externa kostnader (5000-6999) = 24.5 + 2500 = 2524.5
    # Result = 14559.85 + 0.65 - 2524.5 = 12036.00
    assert stmt.annual_result == Decimal("12036")


def test_income_statement_operating_result():
    sie = parse_sie_file(SIE_FILE)
    stmt = generate_income_statement(sie)

    # Should equal annual result since there are no financial items,
    # tax, or appropriations
    assert stmt.operating_result == stmt.annual_result


def test_income_statement_has_correct_structure():
    sie = parse_sie_file(SIE_FILE)
    stmt = generate_income_statement(sie)

    labels = [l.label for l in stmt.lines]
    assert "Rörelseintäkter" in labels
    assert "Nettoomsättning" in labels
    assert "Rörelsekostnader" in labels
    assert "Rörelseresultat" in labels
    assert "Resultat efter finansiella poster" in labels
    assert "Resultat före skatt" in labels
    assert "Årets resultat" in labels
