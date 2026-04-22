"""Equity changes report (Förändringar i eget kapital).

Required by K3 (BFNAR 2012:1 kap 6) for all companies.
Shows movements in each equity component during the fiscal year.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.sie_parser.models import SieFile
from src.financial.income_statement import generate_income_statement


@dataclass
class EquityColumn:
    """One column in the equity changes table."""
    label: str
    opening: Decimal = Decimal(0)
    annual_result: Decimal = Decimal(0)
    dividend: Decimal = Decimal(0)
    new_shares: Decimal = Decimal(0)
    appropriation: Decimal = Decimal(0)  # Disposition of prior year result
    closing: Decimal = Decimal(0)


@dataclass
class EquityChanges:
    columns: list[EquityColumn] = field(default_factory=list)
    total_opening: Decimal = Decimal(0)
    total_closing: Decimal = Decimal(0)
    total_annual_result: Decimal = Decimal(0)
    total_dividend: Decimal = Decimal(0)
    total_appropriation: Decimal = Decimal(0)


def generate_equity_changes(sie: SieFile, year_offset: int = 0) -> EquityChanges:
    """Generate equity changes report."""
    ec = EquityChanges()

    def _ub(start: int, end: int) -> Decimal:
        return sie.sum_ub_range(start, end, year_offset)

    def _ib(acct: str) -> Decimal:
        return sie.get_ib(acct, year_offset)

    def _ub_acct(acct: str) -> Decimal:
        return sie.get_ub(acct, year_offset)

    # Aktiekapital (2081)
    ak_ib = -_ib("2081")
    ak_ub = -_ub_acct("2081")
    ak = EquityColumn(
        label="Aktiekapital",
        opening=ak_ib,
        new_shares=ak_ub - ak_ib,
        closing=ak_ub,
    )
    ec.columns.append(ak)

    # Uppskrivningsfond (2085) if exists
    uppsk_ib = -_ib("2085")
    uppsk_ub = -_ub_acct("2085")
    if uppsk_ib or uppsk_ub:
        col = EquityColumn(
            label="Uppskrivningsfond",
            opening=uppsk_ib,
            closing=uppsk_ub,
        )
        col.appropriation = uppsk_ub - uppsk_ib
        ec.columns.append(col)

    # Reservfond (2086) if exists
    resf_ib = -_ib("2086")
    resf_ub = -_ub_acct("2086")
    if resf_ib or resf_ub:
        col = EquityColumn(
            label="Reservfond",
            opening=resf_ib,
            closing=resf_ub,
        )
        col.appropriation = resf_ub - resf_ib
        ec.columns.append(col)

    # Balanserat resultat (2091 + 2098)
    br_ib = -_ib("2091") + (-_ib("2098"))
    br_ub_before_result = -_ub_acct("2091") + (-_ub_acct("2098"))

    # Årets resultat from income statement
    income_stmt = generate_income_statement(sie, year_offset=year_offset)
    arets_resultat = income_stmt.annual_result

    # The appropriation is the change in balanserat resultat
    # (prior year result moved into retained earnings)
    appropriation = br_ub_before_result - br_ib

    br = EquityColumn(
        label="Balanserat resultat",
        opening=br_ib,
        appropriation=appropriation,
        closing=br_ub_before_result,
    )
    ec.columns.append(br)

    # Årets resultat (separate column)
    # Opening = prior year's result (which has been appropriated), so 0 conceptually
    ar = EquityColumn(
        label="Årets resultat",
        opening=Decimal(0),
        annual_result=arets_resultat,
        appropriation=-appropriation if appropriation else Decimal(0),
        closing=arets_resultat,
    )
    ec.columns.append(ar)

    # Totals
    ec.total_opening = sum((c.opening for c in ec.columns), Decimal(0))
    ec.total_closing = sum((c.closing for c in ec.columns), Decimal(0))
    ec.total_annual_result = arets_resultat
    ec.total_appropriation = Decimal(0)  # Appropriations net to zero

    return ec
