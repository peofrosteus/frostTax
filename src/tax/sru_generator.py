"""SRU file generator for Skatteverket digital filing.

Generates SRU files compatible with Skatteverket's file transfer service
for INK2 (Inkomstdeklaration 2 - aktiebolag).

The file contains three blanketter:
- INK2: Huvudblankett (page 1) – skatteberäkning
- INK2R: Räkenskapsschema – balansräkning + resultaträkning
- INK2S: Skattemässiga justeringar
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from io import StringIO

from src.sie_parser.models import SieFile
from src.tax.sru_mapping import aggregate_sru
from src.tax.ink2_tax_calc import calculate_ink2_tax, INK2_PAGE1_SRU
from src.tax.ink2s_calc import calculate_ink2s, INK2S_SRU


def generate_sru_file(sie: SieFile) -> str:
    """Generate an SRU file for INK2 declaration."""
    buf = StringIO()
    fields = aggregate_sru(sie)

    org_nr = sie.company.org_number.replace("-", "")
    org_nr_16 = "16" + org_nr  # 16-prefix for juridisk person
    company_name = sie.company.name

    fiscal_start = ""
    fiscal_end = ""
    if sie.company.fiscal_year_start:
        fiscal_start = sie.company.fiscal_year_start.strftime("%Y%m%d")
    if sie.company.fiscal_year_end:
        fiscal_end = sie.company.fiscal_year_end.strftime("%Y%m%d")

    now = datetime.now()
    today = now.strftime("%Y%m%d")
    timestamp = now.strftime("%H%M%S")
    blankett_suffix = _blankett_suffix(sie)

    # Parse postal info from SIE address
    postnr, postort = _parse_postal(sie.company.address_postal)

    # --- File header (DATABESKRIVNING) ---
    buf.write("#DATABESKRIVNING_START\n")
    buf.write("#PRODUKT SRU\n")
    buf.write(f"#SKAPAD {today} {timestamp}\n")
    buf.write("#PROGRAM frostTax\n")
    buf.write("#FILNAMN BLANKETTER.SRU\n")
    buf.write("#DATABESKRIVNING_SLUT\n")

    # --- MEDIELEV (org info) ---
    buf.write("#MEDIELEV_START\n")
    buf.write(f"#ORGNR {org_nr_16}\n")
    buf.write(f"#NAMN {company_name}\n")
    if postnr:
        buf.write(f"#POSTNR {postnr}\n")
    if postort:
        buf.write(f"#POSTORT {postort}\n")
    buf.write("#MEDIELEV_SLUT\n")

    # --- Blankett 1: INK2 (page 1 – skatteberäkning) ---
    _write_blankett_header(buf, f"INK2-{blankett_suffix}", org_nr_16, today, timestamp,
                           company_name, fiscal_start, fiscal_end)
    tax_calc = calculate_ink2_tax(sie)
    # Output ALL INK2 page 1 fields (including zeros)
    for tf in tax_calc.fields:
        if tf.field_id in INK2_PAGE1_SRU:
            sru_code = INK2_PAGE1_SRU[tf.field_id]
            buf.write(f"#UPPGIFT {sru_code} {round(tf.amount)}\n")
    buf.write("#BLANKETTSLUT\n")

    # --- Blankett 2: INK2R (räkenskapsschema) ---
    _write_blankett_header(buf, f"INK2R-{blankett_suffix}", org_nr_16, today, timestamp,
                           company_name, fiscal_start, fiscal_end)
    for f in fields:
        amount_rounded = round(f.amount)
        if amount_rounded != 0:
            buf.write(f"#UPPGIFT {f.sru_code} {amount_rounded}\n")
    buf.write("#BLANKETTSLUT\n")

    # --- Blankett 3: INK2S (skattemässiga justeringar) ---
    _write_blankett_header(buf, f"INK2S-{blankett_suffix}", org_nr_16, today, timestamp,
                           company_name, fiscal_start, fiscal_end)
    ink2s = calculate_ink2s(sie)
    for sf in ink2s.fields:
        if sf.field_id in INK2S_SRU and sf.amount != 0:
            sru_code = INK2S_SRU[sf.field_id]
            buf.write(f"#UPPGIFT {sru_code} {round(sf.amount)}\n")
    buf.write("#BLANKETTSLUT\n")

    buf.write("#FIL_SLUT\n")
    return buf.getvalue()


def _write_blankett_header(
    buf: StringIO,
    blankett_id: str,
    org_nr_16: str,
    today: str,
    timestamp: str,
    company_name: str,
    fiscal_start: str,
    fiscal_end: str,
) -> None:
    """Write a blankett header section."""
    buf.write(f"#BLANKETT {blankett_id}\n")
    buf.write(f"#IDENTITET {org_nr_16} {today} {timestamp}\n")
    buf.write(f"#NAMN {company_name}\n")
    if fiscal_start and fiscal_end:
        buf.write(f"#UPPGIFT 7011 {fiscal_start}\n")
        buf.write(f"#UPPGIFT 7012 {fiscal_end}\n")


def _blankett_suffix(sie: SieFile) -> str:
    """Get the blankett name suffix, e.g. '2025P4'."""
    if sie.company.fiscal_year_end:
        return f"{sie.company.fiscal_year_end.year}P4"
    return f"{date.today().year - 1}P4"


def _parse_postal(address_postal: str) -> tuple[str, str]:
    """Parse '18150 Lidingö' into ('18150', 'Lidingö')."""
    if not address_postal:
        return "", ""
    parts = address_postal.strip().split(None, 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", ""
