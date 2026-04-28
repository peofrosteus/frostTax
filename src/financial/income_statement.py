"""Income statement (Resultaträkning) generation per K2 (BFNAR 2016:10).

Cost-by-nature classification (kostnadsslagsindelad).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.sie_parser.models import SieFile


@dataclass
class LineItem:
    """A single line in the income statement."""
    label: str
    amount: Decimal = Decimal(0)
    previous_amount: Decimal = Decimal(0)
    note: str = ""
    is_sum: bool = False
    indent: int = 0


@dataclass
class IncomeStatement:
    lines: list[LineItem] = field(default_factory=list)

    @property
    def net_revenue(self) -> Decimal:
        return self._find("Nettoomsättning")

    @property
    def operating_result(self) -> Decimal:
        return self._find("Rörelseresultat")

    @property
    def result_after_financial(self) -> Decimal:
        return self._find("Resultat efter finansiella poster")

    @property
    def result_before_tax(self) -> Decimal:
        return self._find("Resultat före skatt")

    @property
    def annual_result(self) -> Decimal:
        return self._find("Årets resultat")

    def _find(self, label: str) -> Decimal:
        for li in self.lines:
            if li.label == label:
                return li.amount
        return Decimal(0)


def generate_income_statement(
    sie: SieFile,
    year_offset: int = 0,
) -> IncomeStatement:
    """Generate an income statement from SIE data.

    Uses cost-by-nature classification (kostnadsslagsindelad).
    Revenue accounts are negative in SIE (credit), costs are positive (debit).
    We negate to show revenue as positive and costs as negative in the report.
    """
    stmt = IncomeStatement()

    def _sum(start: int, end: int) -> Decimal:
        return sie.sum_result_range(start, end, year_offset)

    def _prev(start: int, end: int) -> Decimal:
        return sie.sum_result_range(start, end, year_offset - 1)

    # --- Rörelseintäkter ---
    # 3000-3799 includes main revenue (30-36xx) and adjustments/rabatter (37xx)
    nettoomsattning = -_sum(3000, 3799)
    nettoomsattning_prev = -_prev(3000, 3799)

    forandring_lager = -_sum(4900, 4999)
    forandring_lager_prev = -_prev(4900, 4999)

    aktiverat_arbete = -_sum(3800, 3899)
    aktiverat_arbete_prev = -_prev(3800, 3899)

    ovriga_rorelseintakter = -_sum(3900, 3999)
    ovriga_rorelseintakter_prev = -_prev(3900, 3999)

    # --- Rörelsekostnader ---
    ravaror = _sum(4000, 4899)  # Already positive = cost
    ravaror_prev = _prev(4000, 4899)

    ovriga_externa = _sum(5000, 6999)
    ovriga_externa_prev = _prev(5000, 6999)

    personalkostnader = _sum(7000, 7699)
    personalkostnader_prev = _prev(7000, 7699)

    avskrivningar = _sum(7700, 7899)
    avskrivningar_prev = _prev(7700, 7899)

    ovriga_rorelsekostnader = _sum(7900, 7999)
    ovriga_rorelsekostnader_prev = _prev(7900, 7999)

    # --- Finansiella poster ---
    finansiella_intakter = -_sum(8000, 8399)
    finansiella_intakter_prev = -_prev(8000, 8399)

    finansiella_kostnader = _sum(8400, 8799)
    finansiella_kostnader_prev = _prev(8400, 8799)

    # --- Bokslutsdispositioner ---
    bokslutsdispositioner = _sum(8800, 8899)
    bokslutsdispositioner_prev = _prev(8800, 8899)

    # --- Skatt ---
    skatt = _sum(8900, 8989)
    skatt_prev = _prev(8900, 8989)

    # --- Calculate sums ---
    sum_rorelseintakter = (
        nettoomsattning + forandring_lager + aktiverat_arbete + ovriga_rorelseintakter
    )
    sum_rorelseintakter_prev = (
        nettoomsattning_prev + forandring_lager_prev
        + aktiverat_arbete_prev + ovriga_rorelseintakter_prev
    )

    sum_rorelsekostnader = -(
        ravaror + ovriga_externa + personalkostnader
        + avskrivningar + ovriga_rorelsekostnader
    )
    sum_rorelsekostnader_prev = -(
        ravaror_prev + ovriga_externa_prev + personalkostnader_prev
        + avskrivningar_prev + ovriga_rorelsekostnader_prev
    )

    rorelseresultat = sum_rorelseintakter + sum_rorelsekostnader
    rorelseresultat_prev = sum_rorelseintakter_prev + sum_rorelsekostnader_prev

    resultat_efter_finansiella = (
        rorelseresultat + finansiella_intakter - finansiella_kostnader
    )
    resultat_efter_finansiella_prev = (
        rorelseresultat_prev + finansiella_intakter_prev - finansiella_kostnader_prev
    )

    resultat_fore_skatt = resultat_efter_finansiella - bokslutsdispositioner
    resultat_fore_skatt_prev = resultat_efter_finansiella_prev - bokslutsdispositioner_prev

    arets_resultat = resultat_fore_skatt - skatt
    arets_resultat_prev = resultat_fore_skatt_prev - skatt_prev

    # --- Build line items ---
    _add = stmt.lines.append

    _add(LineItem("Rörelseintäkter", is_sum=True))
    _add(LineItem("Nettoomsättning", nettoomsattning, nettoomsattning_prev, indent=1))

    if forandring_lager:
        _add(LineItem(
            "Förändring av lager av produkter i arbete, färdiga varor och pågående arbete",
            forandring_lager, forandring_lager_prev, indent=1,
        ))
    if aktiverat_arbete:
        _add(LineItem(
            "Aktiverat arbete för egen räkning",
            aktiverat_arbete, aktiverat_arbete_prev, indent=1,
        ))
    if ovriga_rorelseintakter:
        _add(LineItem(
            "Övriga rörelseintäkter", ovriga_rorelseintakter, ovriga_rorelseintakter_prev, indent=1,
        ))

    _add(LineItem("Summa rörelseintäkter", sum_rorelseintakter, sum_rorelseintakter_prev, is_sum=True))

    _add(LineItem("Rörelsekostnader", is_sum=True))

    if ravaror:
        _add(LineItem(
            "Råvaror och förnödenheter", -ravaror, -ravaror_prev, indent=1,
        ))
    if ovriga_externa:
        _add(LineItem(
            "Övriga externa kostnader", -ovriga_externa, -ovriga_externa_prev, indent=1,
        ))
    if personalkostnader:
        _add(LineItem("Personalkostnader", -personalkostnader, -personalkostnader_prev, indent=1))
    if avskrivningar:
        _add(LineItem(
            "Av- och nedskrivningar av materiella och immateriella anläggningstillgångar",
            -avskrivningar, -avskrivningar_prev, indent=1,
        ))
    if ovriga_rorelsekostnader:
        _add(LineItem(
            "Övriga rörelsekostnader", -ovriga_rorelsekostnader, -ovriga_rorelsekostnader_prev, indent=1,
        ))

    _add(LineItem("Summa rörelsekostnader", sum_rorelsekostnader, sum_rorelsekostnader_prev, is_sum=True))
    _add(LineItem("Rörelseresultat", rorelseresultat, rorelseresultat_prev, is_sum=True))

    # Financial items
    if finansiella_intakter or finansiella_kostnader:
        _add(LineItem("Finansiella poster", is_sum=True))
        if finansiella_intakter:
            _add(LineItem(
                "Övriga ränteintäkter och liknande resultatposter",
                finansiella_intakter, finansiella_intakter_prev, indent=1,
            ))
        if finansiella_kostnader:
            _add(LineItem(
                "Räntekostnader och liknande resultatposter",
                -finansiella_kostnader, -finansiella_kostnader_prev, indent=1,
            ))
        _add(LineItem(
            "Resultat efter finansiella poster",
            resultat_efter_finansiella, resultat_efter_finansiella_prev, is_sum=True,
        ))
    else:
        _add(LineItem(
            "Resultat efter finansiella poster",
            resultat_efter_finansiella, resultat_efter_finansiella_prev, is_sum=True,
        ))

    # Appropriations
    if bokslutsdispositioner:
        _add(LineItem("Bokslutsdispositioner", -bokslutsdispositioner, -bokslutsdispositioner_prev))

    _add(LineItem("Resultat före skatt", resultat_fore_skatt, resultat_fore_skatt_prev, is_sum=True))

    if skatt:
        _add(LineItem("Skatt på årets resultat", -skatt, -skatt_prev))

    _add(LineItem("Årets resultat", arets_resultat, arets_resultat_prev, is_sum=True))

    return stmt
