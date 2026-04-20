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
    operating_result: Decimal = Decimal(0)
    annual_result: Decimal = Decimal(0)
    total_assets: Decimal = Decimal(0)


@dataclass
class ManagementReport:
    company_name: str = ""
    org_number: str = ""
    fiscal_year: str = ""  # e.g. "2025-01-01 – 2025-12-31"

    # User-editable fields
    business_description: str = ""
    significant_events: str = ""
    expected_future_development: str = ""
    profit_disposition_text: str = ""

    # Calculated
    annual_result: Decimal = Decimal(0)
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
        f"Bolaget bedriver konsultverksamhet."
    )
    report.significant_events = significant_events
    report.expected_future_development = expected_future_development

    # Income statement for current year
    income_stmt = generate_income_statement(sie, year_offset=0)
    balance = generate_balance_sheet(sie, year_offset=0)

    report.annual_result = income_stmt.annual_result

    # Build multi-year overview (current year)
    if sie.company.fiscal_year_end:
        year_label = str(sie.company.fiscal_year_end.year)
    else:
        year_label = "Aktuellt år"

    report.multi_year_overview.append(MultiYearOverview(
        year=year_label,
        net_revenue=income_stmt.net_revenue,
        operating_result=income_stmt.operating_result,
        annual_result=income_stmt.annual_result,
        total_assets=balance.total_assets,
    ))

    # Profit disposition
    if not profit_disposition_text:
        if report.annual_result >= 0:
            report.profit_disposition_text = (
                f"Styrelsen föreslår att till förfogande stående medel, "
                f"årets resultat {_fmt(report.annual_result)} kr, "
                f"balanseras i ny räkning."
            )
        else:
            report.profit_disposition_text = (
                f"Styrelsen föreslår att årets förlust {_fmt(report.annual_result)} kr "
                f"balanseras i ny räkning."
            )
    else:
        report.profit_disposition_text = profit_disposition_text

    return report


def _fmt(value: Decimal) -> str:
    """Format a decimal as Swedish currency string."""
    return f"{value:,.0f}".replace(",", " ")
