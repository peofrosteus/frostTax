"""INK2 page 1 – fields 1.1 through 1.16.

Models the actual INK2 first page (INK2M) as per Skatteverkets blankett.
Fields 1.1–1.2 hold the taxable income from INK2S (4.15/4.16).
Fields 1.3–1.16 cover riskskatt, SLP, avkastningsskatt,
fastighetsavgift/-skatt and skattereduktion.

The detailed computation of överskott/underskott is done in ink2s_calc.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from src.sie_parser.models import SieFile

# Bolagsskattesats
CORPORATE_TAX_RATE = Decimal("0.206")


@dataclass
class TaxField:
    """A single field on INK2 page 1."""
    field_id: str     # e.g. "1.1"
    label: str
    amount: Decimal = Decimal(0)
    editable: bool = False
    details: list[tuple[str, str, Decimal]] = field(default_factory=list)


@dataclass
class Ink2TaxCalculation:
    """Complete INK2 page 1."""
    fields: list[TaxField] = field(default_factory=list)

    def get_field(self, field_id: str) -> TaxField:
        for f in self.fields:
            if f.field_id == field_id:
                return f
        return TaxField(field_id=field_id, label="Okänt fält")

    @property
    def overskott(self) -> Decimal:
        return self.get_field("1.1").amount

    @property
    def underskott(self) -> Decimal:
        return self.get_field("1.2").amount


# SRU field codes for INK2 page 1
# Source: srufiler.se/sru-filer/blanketter/ink2-inkomstdeklaration-2
INK2_PAGE1_SRU: dict[str, str] = {
    "1.1": "7104",    # Överskott av näringsverksamhet
    "1.2": "7114",    # Underskott av näringsverksamhet
    "1.3": "7131",    # Kreditinstituts underlag för riskskatt
    "1.4": "7132",    # Underlag för SLP pensionskostnader
    "1.5": "7133",    # Negativt underlag för SLP
    "1.6a": "7153",   # Avkastningsskatt försäkring 15 %
    "1.6b": "7154",   # Utländska pensionsförskringar 15 %
    "1.7a": "7155",   # Avkastningsskatt försäkring 30 %
    "1.7b": "7156",   # Utländska kapitalförsäkringar 30 %
    "1.8": "80",      # Fastighetsavgift småhus
    "1.9": "93",      # Fastighetsavgift hyreshus bostäder
    "1.10": "84",     # Fastighetsskatt småhus tomtmark
    "1.11": "86",     # Fastighetsskatt hyreshus tomtmark
    "1.12": "95",     # Fastighetsskatt hyreshus lokaler
    "1.13": "96",     # Fastighetsskatt industri/värmekraftverk
    "1.14": "97",     # Fastighetsskatt vattenkraftverk
    "1.15": "98",     # Fastighetsskatt vindkraftverk
    "1.16": "1582",   # Förnybar el (kilowattimmar)
}


def calculate_ink2_tax(sie: SieFile) -> Ink2TaxCalculation:
    """Calculate INK2 page 1 fields 1.1–1.16.

    The taxable income (överskott/underskott) is derived from the INK2S
    computation.  We import and run ink2s here to get 4.15/4.16.
    """
    from src.tax.ink2s_calc import calculate_ink2s

    calc = Ink2TaxCalculation()
    ink2s = calculate_ink2s(sie)
    _add = calc.fields.append

    # ── Underlag för inkomstskatt ──
    _add(TaxField("1.1", "Överskott av näringsverksamhet",
                   ink2s.overskott))
    _add(TaxField("1.2", "Underskott av näringsverksamhet",
                   ink2s.underskott))

    # ── Underlag för riskskatt ──
    _add(TaxField("1.3", "Kreditinstituts underlag för riskskatt",
                   Decimal(0), editable=True))

    # ── Underlag för särskild löneskatt ──
    # Field 1.4 contains the UNDERLAG (pension costs), not the tax.
    # Skatteverket calculates SLP (24.26%) from the underlag.
    # SKV 294: "Observera att det är underlaget, inte skatten, som ska redovisas."
    pensionskostnader = Decimal(0)
    for acct_num in sie.accounts:
        try:
            n = int(acct_num)
        except ValueError:
            continue
        if 7410 <= n <= 7499:
            pensionskostnader += abs(sie.get_result(acct_num, 0))

    _add(TaxField("1.4", "Underlag för särskild löneskatt på pensionskostnader",
                   pensionskostnader, editable=True))
    _add(TaxField("1.5", "Negativt underlag för särskild löneskatt på pensionskostnader",
                   Decimal(0), editable=True))

    # ── Underlag för avkastningsskatt ──
    _add(TaxField("1.6a", "Försäkringsföretag m.fl. samt avsatt till pensioner 15 %",
                   Decimal(0), editable=True))
    _add(TaxField("1.6b", "Utländska pensionsförsäkringar 15 %",
                   Decimal(0), editable=True))
    _add(TaxField("1.7a", "Försäkringsföretag m.fl 30 %",
                   Decimal(0), editable=True))
    _add(TaxField("1.7b", "Utländska kapitalförsäkringar 30 %",
                   Decimal(0), editable=True))

    # ── Underlag för fastighetsavgift ──
    _add(TaxField("1.8", "Småhus/ägarlägenhet",
                   Decimal(0), editable=True))
    _add(TaxField("1.9", "Hyreshus: bostäder",
                   Decimal(0), editable=True))

    # ── Underlag för fastighetsskatt ──
    _add(TaxField("1.10", "Småhus/ägarlägenhet: tomtmark, byggnad under uppförande",
                   Decimal(0), editable=True))
    _add(TaxField("1.11", "Hyreshus: tomtmark, bostäder under uppförande",
                   Decimal(0), editable=True))
    _add(TaxField("1.12", "Hyreshus: lokaler",
                   Decimal(0), editable=True))
    _add(TaxField("1.13", "Industrienhet och elproduktionsenhet: värmekraftverk",
                   Decimal(0), editable=True))
    _add(TaxField("1.14", "Elproduktionsenhet: vattenkraftverk",
                   Decimal(0), editable=True))
    _add(TaxField("1.15", "Elproduktionsenhet: vindkraftverk",
                   Decimal(0), editable=True))

    # ── Underlag för skattereduktion ──
    _add(TaxField("1.16", "Förnybar el (kilowattimmar)",
                   Decimal(0), editable=True))

    return calc
