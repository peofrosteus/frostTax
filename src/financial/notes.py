"""Notes (Noter) generation for the annual report."""

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


def generate_notes(sie: SieFile, framework: str = "K2") -> Notes:
    """Generate notes for the annual report."""
    notes = Notes()
    note_num = 1

    # Not 1: Redovisningsprinciper
    if framework == "K2":
        content = (
            "Årsredovisningen har upprättats i enlighet med årsredovisningslagen "
            "och Bokföringsnämndens allmänna råd (BFNAR 2016:10) om årsredovisning "
            "i mindre företag (K2).\n\n"
            "Intäkter redovisas till verkligt värde av vad som erhållits eller kommer "
            "att erhållas."
        )
    else:
        content = (
            "Årsredovisningen har upprättats i enlighet med årsredovisningslagen "
            "och Bokföringsnämndens allmänna råd (BFNAR 2012:1) om årsredovisning "
            "och koncernredovisning (K3).\n\n"
            "Intäkter redovisas till verkligt värde av vad som erhållits eller kommer "
            "att erhållas."
        )
    notes.items.append(Note(number=note_num, title="Redovisnings- och värderingsprinciper", content=content))
    note_num += 1

    # Not 2: Medelantal anställda (if applicable)
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
        else "Medelantalet anställda under räkenskapsåret.",
    ))
    note_num += 1

    # Check for tangible/intangible assets
    has_immateriella = sie.sum_ub_range(1000, 1099) != 0
    has_materiella = sie.sum_ub_range(1100, 1299) != 0

    if has_immateriella:
        notes.items.append(Note(
            number=note_num,
            title="Immateriella anläggningstillgångar",
            content="Immateriella anläggningstillgångar skrivs av linjärt över bedömd nyttjandeperiod.",
        ))
        note_num += 1

    if has_materiella:
        notes.items.append(Note(
            number=note_num,
            title="Materiella anläggningstillgångar",
            content="Materiella anläggningstillgångar redovisas till anskaffningsvärde minskat med "
                    "ackumulerade avskrivningar och eventuella nedskrivningar.",
        ))
        note_num += 1

    # Check for accrued items
    has_accrued_expenses = sie.sum_ub_range(2900, 2999) != 0
    if has_accrued_expenses:
        accrued_amount = -sie.sum_ub_range(2900, 2999)
        notes.items.append(Note(
            number=note_num,
            title="Upplupna kostnader och förutbetalda intäkter",
            table=[("Upplupna kostnader och förutbetalda intäkter", f"{accrued_amount:,.0f} kr")],
        ))
        note_num += 1

    return notes
