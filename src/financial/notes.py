"""Notes (Noter) generation for the annual report (K2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.sie_parser.models import SieFile


@dataclass
class Note:
    number: int
    title: str
    content: str = ""
    table: list[tuple[str, str]] = field(default_factory=list)  # (label, value) pairs


@dataclass
class Notes:
    items: list[Note] = field(default_factory=list)


# ── Anläggningstillgångar grupperade per K2-kategori ──
# Varje kategori = (titel, asset_intervall, avskrivnings_intervall_PL, redovisningsprincip-text)
# asset_intervall: lista av (low, high)-tuplar; konton som slutar på 9 räknas som ackumulerade avskrivningar.
# avskrivnings_intervall_PL: lista av (low, high)-tuplar för resultatkonton (årets avskrivning).

IMMATERIELLA_KATEGORIER: list[tuple[str, list[tuple[int, int]], list[tuple[int, int]], str]] = [
    (
        "Balanserade utgifter för utvecklingsarbeten",
        [(1010, 1019)],
        [(7811, 7811)],
        "Balanserade utgifter skrivs av linjärt över bedömd nyttjandeperiod, normalt 5 år.",
    ),
    (
        "Koncessioner, patent, licenser, varumärken och liknande rättigheter",
        [(1020, 1039)],
        [(7812, 7815), (7818, 7819)],
        "Koncessioner, patent, licenser och varumärken skrivs av linjärt över bedömd nyttjandeperiod.",
    ),
    (
        "Hyresrätter och liknande rättigheter",
        [(1040, 1049), (1060, 1069)],
        [(7816, 7816)],
        "Hyresrätter och liknande rättigheter skrivs av linjärt över avtalstiden.",
    ),
    (
        "Goodwill",
        [(1050, 1059)],
        [(7817, 7817)],
        "Goodwill skrivs av linjärt över 5 år.",
    ),
    (
        "Förskott avseende immateriella anläggningstillgångar",
        [(1080, 1099)],
        [],
        "Förskott avseende immateriella anläggningstillgångar skrivs inte av.",
    ),
]

MATERIELLA_KATEGORIER: list[tuple[str, list[tuple[int, int]], list[tuple[int, int]], str]] = [
    (
        "Byggnader och mark",
        [(1110, 1119), (1130, 1199)],
        [(7820, 7821), (7824, 7829)],
        "Byggnader skrivs av linjärt över bedömd nyttjandeperiod (typiskt 25–50 år). Mark skrivs inte av.",
    ),
    (
        "Förbättringsutgifter på annans fastighet",
        [(1120, 1129)],
        [(7822, 7823)],
        "Förbättringsutgifter på annans fastighet skrivs av linjärt över avtalstiden eller bedömd nyttjandeperiod.",
    ),
    (
        "Maskiner och andra tekniska anläggningar",
        [(1210, 1219)],
        [(7830, 7831)],
        "Maskiner och andra tekniska anläggningar skrivs av linjärt över bedömd nyttjandeperiod (typiskt 5–10 år).",
    ),
    (
        "Inventarier, verktyg och installationer",
        [(1220, 1269)],
        [(7832, 7839)],
        "Inventarier, verktyg och installationer skrivs av linjärt över bedömd nyttjandeperiod (typiskt 5 år).",
    ),
    (
        "Övriga materiella anläggningstillgångar",
        [(1290, 1299)],
        [],
        "Övriga materiella anläggningstillgångar skrivs av linjärt över bedömd nyttjandeperiod.",
    ),
]


def generate_notes(sie: SieFile) -> Notes:
    """Generate notes for the annual report (K2)."""
    notes = Notes()
    note_num = 1

    # Not 1: Redovisningsprinciper
    content = (
        "Årsredovisningen har upprättats i enlighet med årsredovisningslagen "
        "och Bokföringsnämndens allmänna råd (BFNAR 2016:10) om årsredovisning "
        "i mindre företag (K2).\n\n"
        "Intäkter redovisas till verkligt värde av vad som erhållits eller kommer "
        "att erhållas."
    )
    notes.items.append(Note(number=note_num, title="Redovisnings- och värderingsprinciper", content=content))
    note_num += 1

    # Not 2: Medelantal anställda
    has_salary_accounts = any(
        int(a.number) >= 7000 and int(a.number) <= 7699
        for a in sie.accounts.values()
        if a.number.isdigit() and sie.get_result(a.number) != 0
    )
    notes.items.append(Note(
        number=note_num,
        title="Medelantal anställda",
        content="Bolaget har inte haft några anställda under räkenskapsåret."
        if not has_salary_accounts
        else "Medelantalet anställda under räkenskapsåret har uppgått till ___.",
    ))
    note_num += 1

    # Per-kategori avskrivningstabeller (K2 5.5)
    for title, asset_ranges, depr_ranges, principle in IMMATERIELLA_KATEGORIER + MATERIELLA_KATEGORIER:
        table = _build_anlaggning_table(sie, asset_ranges, depr_ranges)
        if table is None:
            continue
        notes.items.append(Note(number=note_num, title=title, content=principle, table=table))
        note_num += 1

    # Not: Checkräkningskredit (K2 5.20) – om kontot 2330 har ett saldo
    checkkredit_ib = sie.get_ib("2330", 0)
    checkkredit_ub = sie.get_ub("2330", 0)
    if checkkredit_ib != 0 or checkkredit_ub != 0:
        # I SIE har checkkredit kreditbalans (negativ); presentera som positiv utnyttjad summa
        utnyttjat = -checkkredit_ub if checkkredit_ub < 0 else Decimal(0)
        notes.items.append(Note(
            number=note_num,
            title="Checkräkningskredit",
            content=(
                f"Bolaget har en beviljad checkräkningskredit. Av krediten har "
                f"{_fmt(utnyttjat)} kr utnyttjats per balansdagen. Beviljad limit: ___ kr "
                f"(kompletteras manuellt)."
            ),
        ))
        note_num += 1

    # Not: Långfristiga skulder som förfaller >5 år (K2 5.18)
    lang_skulder = -sie.sum_ub_range(2300, 2399, 0)
    if lang_skulder > 0:
        notes.items.append(Note(
            number=note_num,
            title="Långfristiga skulder",
            content=(
                "Inga av bolagets långfristiga skulder förfaller till betalning senare "
                "än fem år efter balansdagen. (Justeras manuellt om så är fallet.)"
            ),
        ))
        note_num += 1

    # Not: Upplupna kostnader och förutbetalda intäkter
    accrued_amount = -sie.sum_ub_range(2900, 2999, 0)
    if accrued_amount != 0:
        notes.items.append(Note(
            number=note_num,
            title="Upplupna kostnader och förutbetalda intäkter",
            table=[("Upplupna kostnader och förutbetalda intäkter", _fmt(accrued_amount))],
        ))
        note_num += 1

    # Not: Ställda säkerheter och ansvarsförbindelser (K2 5.11, ÅRL 5:14-15)
    # Måste alltid redovisas, även om inga finns.
    notes.items.append(Note(
        number=note_num,
        title="Ställda säkerheter och ansvarsförbindelser",
        content="Inga ställda säkerheter. Inga ansvarsförbindelser.",
    ))
    note_num += 1

    return notes


def _account_in_ranges(account_num: str, ranges: list[tuple[int, int]]) -> bool:
    try:
        n = int(account_num)
    except ValueError:
        return False
    return any(low <= n <= high for low, high in ranges)


def _build_anlaggning_table(
    sie: SieFile,
    asset_ranges: list[tuple[int, int]],
    depr_pl_ranges: list[tuple[int, int]],
) -> list[tuple[str, str]] | None:
    """Bygg avskrivningstabell för en kategori av anläggningstillgångar.

    Anskaffningsvärden ligger på BAS-konton som inte slutar på 9.
    Ackumulerade avskrivningar ligger på konton som slutar på 9 (kreditbalans).
    Årets avskrivning hämtas från resultatkonton i ``depr_pl_ranges``.

    Returnerar ``None`` om kategorin saknar saldon helt.
    """
    acq_ib = Decimal(0)
    acq_ub = Decimal(0)
    depr_ib = Decimal(0)
    depr_ub = Decimal(0)

    for acct_num in sie.accounts:
        if not _account_in_ranges(acct_num, asset_ranges):
            continue
        if acct_num.endswith("9"):
            depr_ib += -sie.get_ib(acct_num, 0)
            depr_ub += -sie.get_ub(acct_num, 0)
        else:
            acq_ib += sie.get_ib(acct_num, 0)
            acq_ub += sie.get_ub(acct_num, 0)

    if not (acq_ib or acq_ub or depr_ib or depr_ub):
        return None

    arets_avskrivning = Decimal(0)
    for low, high in depr_pl_ranges:
        arets_avskrivning += sie.sum_result_range(low, high, 0)

    return [
        ("Ingående anskaffningsvärde", _fmt(acq_ib)),
        ("Förändring under året", _fmt(acq_ub - acq_ib)),
        ("Utgående anskaffningsvärde", _fmt(acq_ub)),
        ("Ingående ackumulerade avskrivningar", _fmt(-depr_ib)),
        ("Årets avskrivningar", _fmt(-arets_avskrivning)),
        ("Utgående ackumulerade avskrivningar", _fmt(-depr_ub)),
        ("Bokfört värde vid årets slut", _fmt(acq_ub - depr_ub)),
    ]


def _fmt(value: Decimal) -> str:
    """Formatera ett Decimal-belopp i svensk stil med blanksteg som tusentalsavgränsare."""
    return f"{value:,.0f}".replace(",", " ")
