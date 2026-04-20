"""INK2S – Skattemässiga justeringar (fields 4.1–4.22).

Computes tax adjustments starting from årets resultat (from the income
statement / INK2R field 3.26/3.27) and arriving at the taxable income
(överskott/underskott) that flows back to INK2 page 1 fields 1.1/1.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP

from src.sie_parser.models import SieFile
from src.financial.income_statement import generate_income_statement

# Statslåneränta – used for schablonintäkt on periodiseringsfonder
# November 30, 2024 value (for fiscal year 2025 declarations)
STATSLANERANTA = Decimal("0.021")


@dataclass
class Ink2sField:
    """A single field on INK2S."""
    field_id: str       # e.g. "4.1", "4.3a"
    label: str
    amount: Decimal = Decimal(0)
    sign: str = ""      # "+", "-", or "" (informational)
    editable: bool = False
    details: list[tuple[str, str, Decimal]] = field(default_factory=list)


@dataclass
class Ink2sCalculation:
    """Complete INK2S tax adjustment calculation."""
    fields: list[Ink2sField] = field(default_factory=list)

    def get_field(self, field_id: str) -> Ink2sField:
        for f in self.fields:
            if f.field_id == field_id:
                return f
        return Ink2sField(field_id=field_id, label="Okänt fält")

    @property
    def overskott(self) -> Decimal:
        return self.get_field("4.15").amount

    @property
    def underskott(self) -> Decimal:
        return self.get_field("4.16").amount


# SRU codes for INK2S fields
# Source: srufiler.se/sru-filer/blanketter/ink2s-skattemassiga-justeringar
INK2S_SRU: dict[str, str] = {
    "4.1": "7650",    # Årets resultat, vinst
    "4.2": "7750",    # Årets resultat, förlust
    "4.3a": "7651",   # Skatt på årets resultat
    "4.3b": "7652",   # Nedskrivning av finansiella tillgångar
    "4.3c": "7653",   # Andra bokförda kostnader
    "4.4a": "7751",   # Lämnade koncernbidrag
    "4.4b": "7764",   # Andra ej bokförda kostnader
    "4.5a": "7752",   # Ackordsvinster
    "4.5b": "7753",   # Utdelning
    "4.5c": "7754",   # Andra bokförda intäkter
    "4.6a": "7654",   # Schablonintäkt periodiseringsfonder
    "4.6b": "7668",   # Schablonintäkt fondandelar
    "4.6c": "7655",   # Mottagna koncernbidrag
    "4.6d": "7667",   # Uppräknat belopp periodiseringsfond
    "4.6e": "7665",   # Andra ej bokförda intäkter
    "4.7a": "7755",   # Bokförd vinst
    "4.7b": "7656",   # Bokförd förlust
    "4.7c": "7756",   # Uppskov kapitalvinst N4
    "4.7d": "7657",   # Återfört uppskov N4
    "4.7e": "7658",   # Kapitalvinst
    "4.7f": "7757",   # Kapitalförlust
    "4.8a": "7758",   # Bokförd intäkt/vinst HB
    "4.8b": "7659",   # Skattemässigt överskott N3B
    "4.8c": "7660",   # Bokförd kostnad/förlust HB
    "4.8d": "7759",   # Skattemässigt underskott N3B
    "4.9": "7666",    # Justering avskrivning byggnader/inventarier
    "4.10": "7661",   # Justering avyttring fastighet
    "4.11": "7761",   # Skogsavdrag
    "4.12": "7662",   # Återföringar fastighet
    "4.13": "7663",   # Andra skattemässiga justeringar
    "4.14a": "7763",  # Outnyttjat underskott
    "4.14b": "7664",  # Reduktion beloppsspärr
    "4.14c": "7670",  # Reduktion koncernbidragsspärr
    "4.15": "8020",   # Överskott
    "4.16": "8021",   # Underskott
}


def calculate_ink2s(sie: SieFile) -> Ink2sCalculation:
    """Calculate INK2S fields 4.1–4.22 from SIE data."""
    calc = Ink2sCalculation()
    income_stmt = generate_income_statement(sie, year_offset=0)
    arets_resultat = income_stmt.annual_result
    _add = calc.fields.append

    # ── 4.1 / 4.2: Årets resultat ──
    if arets_resultat >= 0:
        _add(Ink2sField("4.1", "Årets resultat, vinst", arets_resultat, "+"))
        _add(Ink2sField("4.2", "Årets resultat, förlust", Decimal(0), "-"))
    else:
        _add(Ink2sField("4.1", "Årets resultat, vinst", Decimal(0), "+"))
        _add(Ink2sField("4.2", "Årets resultat, förlust", abs(arets_resultat), "-"))

    # ── 4.3: Bokförda kostnader som inte ska dras av ──
    # 4.3a: Skatt på årets resultat
    skatt_resultat = sie.sum_result_range(8900, 8989, 0)
    _add(Ink2sField("4.3a", "Skatt på årets resultat", abs(skatt_resultat), "+"))

    # 4.3b: Nedskrivning av finansiella tillgångar
    nedskrivning_fin = sie.get_result("8270", 0)
    _add(Ink2sField("4.3b", "Nedskrivning av finansiella tillgångar",
                     abs(nedskrivning_fin) if nedskrivning_fin > 0 else Decimal(0), "+",
                     editable=True))

    # 4.3c: Andra bokförda kostnader som inte ska dras av
    ej_avdragsgilla = Decimal(0)
    ej_avdragsgilla_details: list[tuple[str, str, Decimal]] = []
    non_deductible_patterns = ["6072", "6982", "6992", "7622", "7632"]
    for acct_num in non_deductible_patterns:
        amount = sie.get_result(acct_num, 0)
        if amount != 0:
            name = sie.accounts.get(acct_num)
            acct_name = name.name if name else acct_num
            ej_avdragsgilla += abs(amount)
            ej_avdragsgilla_details.append((acct_num, acct_name, abs(amount)))
    # Also scan for accounts with "ej avdragsgill" in the name
    for acct_num, acct in sie.accounts.items():
        if acct_num in non_deductible_patterns:
            continue
        if "ej avdragsgill" in acct.name.lower():
            amount = sie.get_result(acct_num, 0)
            if amount != 0:
                ej_avdragsgilla += abs(amount)
                ej_avdragsgilla_details.append((acct_num, acct.name, abs(amount)))
    _add(Ink2sField("4.3c", "Andra bokförda kostnader", ej_avdragsgilla, "+",
                     editable=True, details=ej_avdragsgilla_details))

    # ── 4.4: Kostnader som ska dras av men inte ingår i resultatet ──
    # 4.4a: Lämnade koncernbidrag (already in 3.19 if booked)
    lamnade_kb = Decimal(0)  # Manual entry typically
    _add(Ink2sField("4.4a", "Lämnade koncernbidrag", lamnade_kb, "-", editable=True))

    # 4.4b: Andra ej bokförda kostnader
    _add(Ink2sField("4.4b", "Andra ej bokförda kostnader", Decimal(0), "-", editable=True))

    # ── 4.5: Bokförda intäkter som inte ska tas upp ──
    # 4.5a: Ackordsvinster
    _add(Ink2sField("4.5a", "Ackordsvinster", Decimal(0), "-", editable=True))

    # 4.5b: Utdelning (skattefri näringsbetingad utdelning)
    utdelning = Decimal(0)
    utdelning_details: list[tuple[str, str, Decimal]] = []
    for acct_num, acct in sie.accounts.items():
        if "utdelning" in acct.name.lower() or acct_num in ("8210", "8220"):
            amount = sie.get_result(acct_num, 0)
            if amount != 0:
                utdelning += abs(amount)
                utdelning_details.append((acct_num, acct.name, abs(amount)))
    _add(Ink2sField("4.5b", "Utdelning", utdelning, "-",
                     editable=True, details=utdelning_details))

    # 4.5c: Andra bokförda intäkter som inte ska tas upp
    skattefria = Decimal(0)
    skattefria_details: list[tuple[str, str, Decimal]] = []
    for acct_num, acct in sie.accounts.items():
        if "skattefri" in acct.name.lower():
            amount = sie.get_result(acct_num, 0)
            if amount != 0:
                skattefria += abs(amount)
                skattefria_details.append((acct_num, acct.name, abs(amount)))
    _add(Ink2sField("4.5c", "Andra bokförda intäkter", skattefria, "-",
                     editable=True, details=skattefria_details))

    # ── 4.6: Intäkter som ska tas upp men inte ingår i resultatet ──
    # 4.6a: Schablonintäkt periodiseringsfonder
    sum_pfond_ib = Decimal(0)
    for acct_num in sie.accounts:
        try:
            n = int(acct_num)
        except ValueError:
            continue
        if 2110 <= n <= 2139:
            sum_pfond_ib += abs(sie.get_ib(acct_num, 0))
    schablonintakt = (sum_pfond_ib * STATSLANERANTA).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    _add(Ink2sField("4.6a", "Beräknad schablonintäkt på periodiseringsfonder",
                     schablonintakt, "+", editable=True))

    # 4.6b: Schablonintäkt fondandelar
    _add(Ink2sField("4.6b", "Beräknad schablonintäkt på fondandelar", Decimal(0), "+",
                     editable=True))

    # 4.6c: Mottagna koncernbidrag
    _add(Ink2sField("4.6c", "Mottagna koncernbidrag", Decimal(0), "+", editable=True))

    # 4.6d: Uppräknat belopp vid återföring av periodiseringsfond
    _add(Ink2sField("4.6d", "Uppräknat belopp vid återföring av periodiseringsfond",
                     Decimal(0), "+", editable=True))

    # 4.6e: Andra ej bokförda intäkter
    _add(Ink2sField("4.6e", "Andra ej bokförda intäkter", Decimal(0), "+", editable=True))

    # ── 4.7: Avyttring av delägarrätter ──
    _add(Ink2sField("4.7a", "Bokförd vinst", Decimal(0), "-", editable=True))
    _add(Ink2sField("4.7b", "Bokförd förlust", Decimal(0), "+", editable=True))
    _add(Ink2sField("4.7c", "Uppskov med kapitalvinst enl. N4", Decimal(0), "-", editable=True))
    _add(Ink2sField("4.7d", "Återfört uppskov av kapitalvinst enl. N4", Decimal(0), "+", editable=True))
    _add(Ink2sField("4.7e", "Kapitalvinst för beskattningsåret", Decimal(0), "+", editable=True))
    _add(Ink2sField("4.7f", "Kapitalförlust som ska dras av", Decimal(0), "-", editable=True))

    # ── 4.8: Andel i handelsbolag ──
    _add(Ink2sField("4.8a", "Bokförd intäkt/vinst", Decimal(0), "-", editable=True))
    _add(Ink2sField("4.8b", "Skattemässigt överskott enl. N3B", Decimal(0), "+", editable=True))
    _add(Ink2sField("4.8c", "Bokförd kostnad/förlust", Decimal(0), "+", editable=True))
    _add(Ink2sField("4.8d", "Skattemässigt underskott enl. N3B", Decimal(0), "-", editable=True))

    # ── 4.9: Skattemässig justering avskrivning byggnader/inventarier ──
    # Positive = ökar det skattemässiga resultatet, negative = minskar
    _add(Ink2sField("4.9", "Skattemässig justering avskrivning byggnader/inventarier", Decimal(0), "+/−", editable=True))

    # ── 4.10: Avyttring av näringsfastighet ──
    _add(Ink2sField("4.10", "Skattemässig justering avyttring fastighet", Decimal(0), "+/−", editable=True))

    # ── 4.11: Skogs-/substansminskningsavdrag ──
    _add(Ink2sField("4.11", "Skogs-/substansminskningsavdrag", Decimal(0), "-", editable=True))

    # ── 4.12: Återföringar vid avyttring av fastighet ──
    _add(Ink2sField("4.12", "Återföringar vid avyttring av fastighet", Decimal(0), "+", editable=True))

    # ── 4.13: Andra skattemässiga justeringar ──
    _add(Ink2sField("4.13", "Andra skattemässiga justeringar", Decimal(0), "+/−", editable=True))

    # ── 4.14: Underskott ──
    _add(Ink2sField("4.14a", "Outnyttjat underskott från föregående år", Decimal(0), "-", editable=True))
    _add(Ink2sField("4.14b", "Reduktion av underskott (beloppsspärr, ackord m.m.)", Decimal(0), "+", editable=True))
    _add(Ink2sField("4.14c", "Reduktion av underskott (koncernbidragsspärr m.m.)", Decimal(0), "+", editable=True))

    # ── Compute 4.15/4.16: Överskott/Underskott ──
    _compute_result(calc)

    # ── Övriga uppgifter (4.17–4.22) ──
    # 4.17: Värdeminskningsavdrag byggnader
    _add(Ink2sField("4.17", "Värdeminskningsavdrag byggnader", Decimal(0), "", editable=True))

    # 4.18: Värdeminskningsavdrag markanläggningar
    _add(Ink2sField("4.18", "Värdeminskningsavdrag markanläggningar", Decimal(0), "", editable=True))

    # 4.19: Restvärdesavskrivning – återförda belopp
    _add(Ink2sField("4.19", "Restvärdesavskrivning: återförda belopp", Decimal(0), "", editable=True))

    # 4.20: Lån från aktieägare
    lan_aktieagare = Decimal(0)
    for acct_num in sie.accounts:
        try:
            n = int(acct_num)
        except ValueError:
            continue
        if 2390 <= n <= 2399:
            lan_aktieagare += abs(sie.get_ub(acct_num, 0))
    _add(Ink2sField("4.20", "Lån från aktieägare (fysisk person) vid beskattningsårets utgång",
                     lan_aktieagare, "", editable=True))

    # 4.21: Pensionskostnader
    pensionskostnader = Decimal(0)
    for acct_num in sie.accounts:
        try:
            n = int(acct_num)
        except ValueError:
            continue
        if 7410 <= n <= 7499:
            pensionskostnader += abs(sie.get_result(acct_num, 0))
    _add(Ink2sField("4.21", "Pensionskostnader (som ingår i p. 3.8)", pensionskostnader, "",
                     editable=True))

    # 4.22: Koncernbidragsspärrat underskott
    _add(Ink2sField("4.22", "Koncernbidragsspärrat och fusionsspärrat underskott",
                     Decimal(0), "", editable=True))

    return calc


def _compute_result(calc: Ink2sCalculation) -> None:
    """Compute fields 4.15 (överskott) and 4.16 (underskott)."""
    g = calc.get_field

    # Start with årets resultat
    result = g("4.1").amount - g("4.2").amount

    # Add back non-deductible costs (4.3)
    result += g("4.3a").amount + g("4.3b").amount + g("4.3c").amount

    # Subtract costs not in the result (4.4)
    result -= g("4.4a").amount + g("4.4b").amount

    # Subtract tax-free income (4.5)
    result -= g("4.5a").amount + g("4.5b").amount + g("4.5c").amount

    # Add income not in the result (4.6)
    result += (g("4.6a").amount + g("4.6b").amount + g("4.6c").amount
               + g("4.6d").amount + g("4.6e").amount)

    # Delägarrätter (4.7)
    result += (-g("4.7a").amount + g("4.7b").amount - g("4.7c").amount
               + g("4.7d").amount + g("4.7e").amount - g("4.7f").amount)

    # Handelsbolag (4.8)
    result += -g("4.8a").amount + g("4.8b").amount + g("4.8c").amount - g("4.8d").amount

    # Avskrivningsjusteringar (4.9) – positive increases, negative decreases
    result += g("4.9").amount

    # Fastighetsjusteringar (4.10) – positive increases, negative decreases
    result += g("4.10").amount

    # Skogsavdrag (4.11) and återföringar (4.12)
    result -= g("4.11").amount
    result += g("4.12").amount

    # Andra justeringar (4.13) – positive increases, negative decreases
    result += g("4.13").amount

    # Underskott (4.14)
    result -= g("4.14a").amount
    result += g("4.14b").amount + g("4.14c").amount

    if result >= 0:
        calc.fields.append(Ink2sField("4.15", "Överskott (flyttas till p. 1.1 på sid. 1)",
                                       result, "+"))
        calc.fields.append(Ink2sField("4.16", "Underskott (flyttas till p. 1.2 på sid. 1)",
                                       Decimal(0), "-"))
    else:
        calc.fields.append(Ink2sField("4.15", "Överskott (flyttas till p. 1.1 på sid. 1)",
                                       Decimal(0), "+"))
        calc.fields.append(Ink2sField("4.16", "Underskott (flyttas till p. 1.2 på sid. 1)",
                                       abs(result), "-"))
