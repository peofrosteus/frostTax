"""SRU file generator for Skatteverket digital filing.

Generates SRU files compatible with Skatteverket's file transfer service
for INK2 (Inkomstdeklaration 2 - aktiebolag).

The file contains three blanketter:
- INK2: Huvudblankett (page 1) – skatteberäkning
- INK2R: Räkenskapsschema – balansräkning + resultaträkning
- INK2S: Skattemässiga justeringar
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import StringIO

from src.sie_parser.models import SieFile
from src.tax.sru_mapping import aggregate_sru
from src.tax.ink2_tax_calc import calculate_ink2_tax
from src.tax.ink2s_calc import calculate_ink2s, INK2S_SRU

# SRU field codes for INK2 page 1 (skatteberäkning)
INK2_PAGE1_SRU = {
    "1.1": "7014",
    "1.2": "7015",
    "1.3": "7016",
    "1.5": "7007",
    "1.7": "7006",
    "1.11": "7017",
    "1.13": "7050",
    "1.14": "7051",
}


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
    tax_year = _tax_year(sie)

    # --- File header ---
    buf.write("#DATABESKRIVNING_START\n")
    buf.write("#PROGRAM frostTax\n")
    buf.write("#FILNAMN BLANKETTER.SRU\n")
    buf.write(f"#SESSION {today}\n")
    buf.write("#FLAGGA 0\n")
    buf.write("#DATABESKRIVNING_SLUT\n")
    buf.write(f"#MEDESSION {today}\n")

    # --- Blankett 1: INK2 (page 1 – skatteberäkning) ---
    _write_blankett_header(buf, f"INK2-{tax_year}", org_nr, today, company_name,
                           fiscal_start, fiscal_end)
    tax_calc = calculate_ink2_tax(sie)
    for tf in tax_calc.fields:
        if tf.field_id in INK2_PAGE1_SRU and tf.amount != 0:
            sru_code = INK2_PAGE1_SRU[tf.field_id]
            buf.write(f"#UPPGIFT {sru_code} {int(tf.amount)}\n")
    buf.write("#BLANKETTSLUT\n")

    # --- Blankett 2: INK2R (räkenskapsschema) ---
    _write_blankett_header(buf, f"INK2R-{tax_year}", org_nr, today, company_name,
                           fiscal_start, fiscal_end)
    for f in fields:
        amount_int = int(f.amount)
        if amount_int != 0:
            buf.write(f"#UPPGIFT {f.sru_code} {amount_int}\n")
    buf.write("#BLANKETTSLUT\n")

    # --- Blankett 3: INK2S (skattemässiga justeringar) ---
    _write_blankett_header(buf, f"INK2S-{tax_year}", org_nr, today, company_name,
                           fiscal_start, fiscal_end)
    ink2s = calculate_ink2s(sie)
    for sf in ink2s.fields:
        if sf.field_id in INK2S_SRU and sf.amount != 0:
            sru_code = INK2S_SRU[sf.field_id]
            buf.write(f"#UPPGIFT {sru_code} {int(sf.amount)}\n")
    buf.write("#BLANKETTSLUT\n")

    buf.write("#FIL_SLUT\n")
    return buf.getvalue()


def _write_blankett_header(
    buf: StringIO,
    blankett_id: str,
    org_nr: str,
    today: str,
    company_name: str,
    fiscal_start: str,
    fiscal_end: str,
) -> None:
    """Write a blankett header section."""
    buf.write(f"#BLANKETT {blankett_id}\n")
    buf.write(f"#IDENTITET {org_nr} {today}\n")
    buf.write(f"#NAMN {company_name}\n")
    buf.write(f"#UPPGIFT 7011 {org_nr}\n")
    if fiscal_start and fiscal_end:
        buf.write(f"#UPPGIFT 7012 {fiscal_start}\n")
        buf.write(f"#UPPGIFT 7013 {fiscal_end}\n")


def _tax_year(sie: SieFile) -> str:
    """Get the tax year (deklarationsår) for the filing."""
    if sie.company.fiscal_year_end:
        # Tax year is the year after the fiscal year ends
        return str(sie.company.fiscal_year_end.year + 1)
    return str(date.today().year)
