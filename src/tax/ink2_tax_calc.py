"""INK2 tax calculation – fields 1.1 through 1.16.

Calculates the skatteberäkning (tax computation) on page 1 of the INK2
declaration form for aktiebolag.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from src.sie_parser.models import SieFile
from src.financial.income_statement import generate_income_statement

# Bolagsskattesats
CORPORATE_TAX_RATE = Decimal("0.206")

# Konton som är ej avdragsgilla (vanliga i EUBAS97)
NON_DEDUCTIBLE_ACCOUNT_PATTERNS = [
    "6072",  # Representation, ej avdragsgill
    "6982",  # Föreningsavgifter, ej avdragsgilla
    "6992",  # Övriga externa kostnader, ej avdragsgilla
    "7622",  # Sjuk- och hälsovård, ej avdragsgill
    "7632",  # Personalrepresentation, ej avdragsgill
]

# Konton med skattefria intäkter
TAX_FREE_INCOME_ACCOUNTS = [
    "8314",  # Skattefria ränteintäkter
]


@dataclass
class TaxField:
    """A single field on INK2 page 1."""
    field_id: str     # e.g. "1.1"
    label: str
    amount: Decimal = Decimal(0)
    editable: bool = False  # Can be manually adjusted by user
    details: list[tuple[str, str, Decimal]] = field(default_factory=list)  # (account, name, amount)


@dataclass
class Ink2TaxCalculation:
    """Complete INK2 page 1 tax calculation."""
    fields: list[TaxField] = field(default_factory=list)

    def get_field(self, field_id: str) -> TaxField:
        for f in self.fields:
            if f.field_id == field_id:
                return f
        return TaxField(field_id=field_id, label="Okänt fält")

    @property
    def tax_to_pay(self) -> Decimal:
        return self.get_field("1.14").amount

    @property
    def taxable_income(self) -> Decimal:
        return self.get_field("1.11").amount


def calculate_ink2_tax(sie: SieFile) -> Ink2TaxCalculation:
    """Calculate INK2 page 1 fields 1.1–1.16."""
    calc = Ink2TaxCalculation()
    income_stmt = generate_income_statement(sie, year_offset=0)

    # --- 1.1 Bokfört resultat ---
    bokfort_resultat = income_stmt.result_before_tax
    calc.fields.append(TaxField(
        field_id="1.1",
        label="Bokfört resultat",
        amount=bokfort_resultat,
    ))

    # --- 1.2 Ej avdragsgilla kostnader ---
    ej_avdragsgilla = Decimal(0)
    ej_avdragsgilla_details: list[tuple[str, str, Decimal]] = []

    # Scan for known non-deductible accounts
    for acct_num in NON_DEDUCTIBLE_ACCOUNT_PATTERNS:
        amount = sie.get_result(acct_num, 0)
        if amount != 0:
            name = sie.accounts.get(acct_num, None)
            acct_name = name.name if name else acct_num
            ej_avdragsgilla += amount
            ej_avdragsgilla_details.append((acct_num, acct_name, amount))

    # Also scan for any account whose name contains "ej avdragsgill"
    for acct_num, acct in sie.accounts.items():
        if acct_num in NON_DEDUCTIBLE_ACCOUNT_PATTERNS:
            continue
        if "ej avdragsgill" in acct.name.lower():
            amount = sie.get_result(acct_num, 0)
            if amount != 0:
                ej_avdragsgilla += amount
                ej_avdragsgilla_details.append((acct_num, acct.name, amount))

    calc.fields.append(TaxField(
        field_id="1.2",
        label="Ej avdragsgilla kostnader",
        amount=ej_avdragsgilla,
        editable=True,
        details=ej_avdragsgilla_details,
    ))

    # --- 1.3 Ej skattepliktiga intäkter ---
    ej_skattepliktiga = Decimal(0)
    ej_skattepliktiga_details: list[tuple[str, str, Decimal]] = []

    for acct_num in TAX_FREE_INCOME_ACCOUNTS:
        amount = sie.get_result(acct_num, 0)
        if amount != 0:
            name = sie.accounts.get(acct_num, None)
            acct_name = name.name if name else acct_num
            ej_skattepliktiga += abs(amount)
            ej_skattepliktiga_details.append((acct_num, acct_name, abs(amount)))

    # Also scan for any account whose name contains "skattefri"
    for acct_num, acct in sie.accounts.items():
        if acct_num in TAX_FREE_INCOME_ACCOUNTS:
            continue
        if "skattefri" in acct.name.lower():
            amount = sie.get_result(acct_num, 0)
            if amount != 0:
                ej_skattepliktiga += abs(amount)
                ej_skattepliktiga_details.append((acct_num, acct.name, abs(amount)))

    calc.fields.append(TaxField(
        field_id="1.3",
        label="Ej skattepliktiga intäkter",
        amount=ej_skattepliktiga,
        editable=True,
        details=ej_skattepliktiga_details,
    ))

    # --- 1.4 Skattemässigt resultat före dispositioner ---
    resultat_fore_disp = bokfort_resultat + ej_avdragsgilla - ej_skattepliktiga
    calc.fields.append(TaxField(
        field_id="1.4",
        label="Skattemässigt resultat före dispositioner",
        amount=resultat_fore_disp,
    ))

    # --- 1.5 Återföring av periodiseringsfond ---
    aterforing_pfond = -sie.get_result("8819", 0)  # Credit → positive
    calc.fields.append(TaxField(
        field_id="1.5",
        label="Återföring av periodiseringsfond",
        amount=aterforing_pfond,
        editable=True,
    ))

    # --- 1.6 Schablonintäkt på periodiseringsfond ---
    # = summa periodiseringsfonder (IB) × statslåneränta (nov 30 föregående år) × 100%
    # Statslåneränta november 2024 ≈ 2.10% (for fiscal year 2025)
    STATSLANERANTA = Decimal("0.021")
    sum_pfond_ib = Decimal(0)
    for acct_num, acct in sie.accounts.items():
        try:
            n = int(acct_num)
        except ValueError:
            continue
        if 2110 <= n <= 2139:
            sum_pfond_ib += abs(sie.get_ib(acct_num, 0))

    schablonintakt = (sum_pfond_ib * STATSLANERANTA).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    calc.fields.append(TaxField(
        field_id="1.6",
        label="Schablonintäkt på periodiseringsfond",
        amount=schablonintakt,
        editable=True,
    ))

    # --- 1.7 Avsättning till periodiseringsfond ---
    avsattning_pfond = sie.get_result("8811", 0)  # Debit = positive in SIE
    calc.fields.append(TaxField(
        field_id="1.7",
        label="Avsättning till periodiseringsfond (max 25% av 1.4)",
        amount=avsattning_pfond,
        editable=True,
    ))

    # --- 1.8 Återföring av överavskrivningar ---
    forandring_overavskr = sie.get_result("8850", 0)
    aterforing_overavskr = forandring_overavskr if forandring_overavskr < 0 else Decimal(0)
    calc.fields.append(TaxField(
        field_id="1.8",
        label="Återföring av överavskrivningar",
        amount=abs(aterforing_overavskr),
        editable=True,
    ))

    # --- 1.9 Avsättning till överavskrivningar ---
    avsattning_overavskr = forandring_overavskr if forandring_overavskr > 0 else Decimal(0)
    calc.fields.append(TaxField(
        field_id="1.9",
        label="Avsättning till överavskrivningar",
        amount=avsattning_overavskr,
        editable=True,
    ))

    # --- 1.10 Outnyttjat underskott från föregående år ---
    # This would need to come from previous year's declaration
    calc.fields.append(TaxField(
        field_id="1.10",
        label="Outnyttjat underskott från föregående år",
        amount=Decimal(0),
        editable=True,
    ))

    # --- 1.11 Överskott av näringsverksamhet ---
    overskott_nv = (
        resultat_fore_disp
        + aterforing_pfond
        + schablonintakt
        - avsattning_pfond
        + abs(aterforing_overavskr)
        - avsattning_overavskr
    )
    calc.fields.append(TaxField(
        field_id="1.11",
        label="Överskott av näringsverksamhet" if overskott_nv >= 0 else "Underskott av näringsverksamhet",
        amount=overskott_nv,
    ))

    # --- 1.12 Underskott att nyttja ---
    underskott_nyttja = min(
        abs(calc.get_field("1.10").amount),
        max(overskott_nv, Decimal(0)),
    )
    calc.fields.append(TaxField(
        field_id="1.12",
        label="Avdrag för underskott föregående år",
        amount=underskott_nyttja,
    ))

    # --- 1.13 Skattemässigt resultat ---
    skattemassigt_resultat = overskott_nv - underskott_nyttja
    calc.fields.append(TaxField(
        field_id="1.13",
        label="Skattemässigt resultat",
        amount=skattemassigt_resultat,
    ))

    # --- 1.14 Skatt på årets resultat (20.6%) ---
    if skattemassigt_resultat > 0:
        skatt = (skattemassigt_resultat * CORPORATE_TAX_RATE).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    else:
        skatt = Decimal(0)

    calc.fields.append(TaxField(
        field_id="1.14",
        label=f"Skatt på årets resultat ({CORPORATE_TAX_RATE * 100}%)",
        amount=skatt,
    ))

    # --- 1.15 Avräkning utländsk skatt ---
    calc.fields.append(TaxField(
        field_id="1.15",
        label="Avräkning utländsk skatt",
        amount=Decimal(0),
        editable=True,
    ))

    # --- 1.16 Skatt att betala ---
    skatt_att_betala = skatt - calc.get_field("1.15").amount
    calc.fields.append(TaxField(
        field_id="1.16",
        label="Skatt att betala",
        amount=skatt_att_betala,
    ))

    return calc
