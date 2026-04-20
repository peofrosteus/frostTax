"""SRU file generator for Skatteverket digital filing.

Generates SRU files compatible with Skatteverket's file transfer service
for INK2 (Inkomstdeklaration 2 - aktiebolag).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import StringIO

from src.sie_parser.models import SieFile
from src.tax.sru_mapping import aggregate_sru


def generate_sru_file(sie: SieFile) -> str:
    """Generate an SRU file for INK2 declaration."""
    buf = StringIO()
    fields = aggregate_sru(sie)

    org_nr = sie.company.org_number.replace("-", "")
    company_name = sie.company.name

    fiscal_start = ""
    fiscal_end = ""
    if sie.company.fiscal_year_start:
        fiscal_start = sie.company.fiscal_year_start.strftime("%Y%m%d")
    if sie.company.fiscal_year_end:
        fiscal_end = sie.company.fiscal_year_end.strftime("%Y%m%d")

    today = date.today().strftime("%Y%m%d")

    # --- Info file section ---
    buf.write("#DATABESKRIVNING_START\n")
    buf.write(f"#PROGRAM frostTax\n")
    buf.write(f"#FILNAMN BLANKETTER.SRU\n")
    buf.write(f"#SESSION {today}\n")
    buf.write(f"#FLAGGA 0\n")
    buf.write("#DATABESKRIVNING_SLUT\n")
    buf.write(f"#MEDESSION {today}\n")

    # --- INK2 blankett ---
    buf.write(f"#BLANKETT INK2-{_tax_year(sie)}\n")
    buf.write(f"#IDENTITET {org_nr} {today}\n")
    buf.write(f"#NAMN {company_name}\n")

    # Orgnr field
    buf.write(f"#UPPGIFT 7011 {org_nr}\n")

    # Fiscal year
    if fiscal_start and fiscal_end:
        buf.write(f"#UPPGIFT 7012 {fiscal_start}\n")
        buf.write(f"#UPPGIFT 7013 {fiscal_end}\n")

    # Write each SRU field
    for f in fields:
        # SRU values: positive amounts are written as-is,
        # negative amounts are written with minus sign.
        # Skatteverket expects whole numbers (öre removed).
        amount_int = int(f.amount)
        buf.write(f"#UPPGIFT {f.sru_code} {amount_int}\n")

    buf.write("#BLANKETTSLUT\n")
    buf.write("#FIL_SLUT\n")

    return buf.getvalue()


def _tax_year(sie: SieFile) -> str:
    """Get the tax year (deklarationsår) for the filing."""
    if sie.company.fiscal_year_end:
        # Tax year is the year after the fiscal year ends
        return str(sie.company.fiscal_year_end.year + 1)
    return str(date.today().year)
