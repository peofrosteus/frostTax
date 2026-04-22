"""Management report (Förvaltningsberättelse) generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.sie_parser.models import SieFile
from src.financial.income_statement import generate_income_statement
from src.financial.balance_sheet import generate_balance_sheet


@dataclass
class MultiYearOverview:
    """Flerårsöversikt."""
    year: str
    net_revenue: Decimal = Decimal(0)
    result_after_financial: Decimal = Decimal(0)
    annual_result: Decimal = Decimal(0)
    total_assets: Decimal = Decimal(0)


@dataclass
class ProfitDisposition:
    """Strukturerad resultatdisposition per K2 4.6."""
    retained_earnings: Decimal = Decimal(0)  # Balanserat resultat
    annual_result: Decimal = Decimal(0)       # Årets resultat
    available_funds: Decimal = Decimal(0)     # Summa fritt eget kapital
    carried_forward: Decimal = Decimal(0)     # I ny räkning överförs


@dataclass
class ManagementReport:
    company_name: str = ""
    org_number: str = ""
    company_location: str = ""  # Bolagets säte (K2 4.2)
    fiscal_year: str = ""  # e.g. "2025-01-01 – 2025-12-31"

    # User-editable fields
    business_description: str = ""
    significant_events: str = ""
    expected_future_development: str = ""
    profit_disposition_text: str = ""  # Override for freeform text

    # Calculated
    annual_result: Decimal = Decimal(0)
    profit_disposition: ProfitDisposition = field(default_factory=ProfitDisposition)
    multi_year_overview: list[MultiYearOverview] = field(default_factory=list)


def generate_management_report(
    sie: SieFile,
    business_description: str = "",
    significant_events: str = "",
    expected_future_development: str = "",
    profit_disposition_text: str = "",
) -> ManagementReport:
    """Generate a management report from SIE data."""
    report = ManagementReport()
    report.company_name = sie.company.name
    report.org_number = sie.company.org_number

    if sie.company.fiscal_year_start and sie.company.fiscal_year_end:
        report.fiscal_year = (
            f"{sie.company.fiscal_year_start.isoformat()} – "
            f"{sie.company.fiscal_year_end.isoformat()}"
        )

    report.business_description = business_description or (
        "Bolaget bedriver konsultverksamhet."
    )
    report.significant_events = significant_events
    report.expected_future_development = expected_future_development

    # Bolagets säte – extract city from postal address (e.g. "17263 Sundbyberg")
    report.company_location = _extract_city(sie.company.address_postal)

    # Income statement for current year
    income_stmt = generate_income_statement(sie, year_offset=0)
    balance = generate_balance_sheet(sie, year_offset=0)

    report.annual_result = income_stmt.annual_result

    # Build multi-year overview (K2 4.5: nettoomsättning, resultat efter fin. poster)
    if sie.has_previous_year:
        prev_income = generate_income_statement(sie, year_offset=-1)
        prev_balance = generate_balance_sheet(sie, year_offset=-1)
        prev_label = str(sie.company.prev_fiscal_year_end.year)
        report.multi_year_overview.append(MultiYearOverview(
            year=prev_label,
            net_revenue=prev_income.net_revenue,
            result_after_financial=prev_income.result_after_financial,
            annual_result=prev_income.annual_result,
            total_assets=prev_balance.total_assets,
        ))

    if sie.company.fiscal_year_end:
        year_label = str(sie.company.fiscal_year_end.year)
    else:
        year_label = "Aktuellt år"

    report.multi_year_overview.append(MultiYearOverview(
        year=year_label,
        net_revenue=income_stmt.net_revenue,
        result_after_financial=income_stmt.result_after_financial,
        annual_result=income_stmt.annual_result,
        total_assets=balance.total_assets,
    ))

    # Structured profit disposition (K2 4.6)
    retained_earnings = -sie.sum_ub_range(2091, 2091) + (-sie.sum_ub_range(2098, 2098))
    available = retained_earnings + report.annual_result
    report.profit_disposition = ProfitDisposition(
        retained_earnings=retained_earnings,
        annual_result=report.annual_result,
        available_funds=available,
        carried_forward=available,
    )

    report.profit_disposition_text = profit_disposition_text

    return report


def _extract_city(postal: str) -> str:
    """Extract city name from a Swedish postal address like '17263 Sundbyberg'."""
    if not postal:
        return ""
    parts = postal.strip().split(None, 1)
    if len(parts) == 2 and parts[0].replace(" ", "").isdigit():
        return parts[1]
    return postal


def _fmt(value: Decimal) -> str:
    """Format a decimal as Swedish currency string."""
    return f"{value:,.0f}".replace(",", " ")
