"""Cash flow statement (Kassaflödesanalys) – indirect method.

Required by K3 (BFNAR 2012:1 kap 7) for all companies.
Uses the indirect method starting from årets resultat.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.sie_parser.models import SieFile


@dataclass
class CashFlowLine:
    label: str
    amount: Decimal = Decimal(0)
    previous_amount: Decimal = Decimal(0)
    is_sum: bool = False
    indent: int = 0


@dataclass
class CashFlowStatement:
    lines: list[CashFlowLine] = field(default_factory=list)

    @property
    def operating_cash_flow(self) -> Decimal:
        return self._find("Kassaflöde från den löpande verksamheten")

    @property
    def investing_cash_flow(self) -> Decimal:
        return self._find("Kassaflöde från investeringsverksamheten")

    @property
    def financing_cash_flow(self) -> Decimal:
        return self._find("Kassaflöde från finansieringsverksamheten")

    @property
    def net_cash_flow(self) -> Decimal:
        return self._find("Årets kassaflöde")

    def _find(self, label: str) -> Decimal:
        for li in self.lines:
            if li.label == label:
                return li.amount
        return Decimal(0)


def generate_cash_flow(sie: SieFile, year_offset: int = 0) -> CashFlowStatement:
    """Generate a cash flow statement using the indirect method."""
    cf = CashFlowStatement()
    _add = cf.lines.append

    def _res(start: int, end: int) -> Decimal:
        return sie.sum_result_range(start, end, year_offset)

    def _prev_res(start: int, end: int) -> Decimal:
        return sie.sum_result_range(start, end, year_offset - 1)

    def _ub(start: int, end: int) -> Decimal:
        return sie.sum_ub_range(start, end, year_offset)

    def _ub_prev(start: int, end: int) -> Decimal:
        return sie.sum_ub_range(start, end, year_offset - 1)

    def _ib(start: int, end: int) -> Decimal:
        total = Decimal(0)
        for acct in sie.accounts_in_range(start, end):
            total += sie.get_ib(acct.number, year_offset)
        return total

    def _ib_prev(start: int, end: int) -> Decimal:
        total = Decimal(0)
        for acct in sie.accounts_in_range(start, end):
            total += sie.get_ib(acct.number, year_offset - 1)
        return total

    # == DEN LÖPANDE VERKSAMHETEN ==
    _add(CashFlowLine("Den löpande verksamheten", is_sum=True))

    # Årets resultat (from income statement accounts 3000-8999)
    arets_resultat = -_res(3000, 8999)
    arets_resultat_prev = -_prev_res(3000, 8999)
    _add(CashFlowLine("Resultat efter finansiella poster", arets_resultat, arets_resultat_prev, indent=1))

    # Adjustments for non-cash items
    _add(CashFlowLine("Justeringar för poster som inte ingår i kassaflödet:", is_sum=True, indent=1))

    # Depreciation & amortization (7700-7899 are debit = positive in SIE)
    avskrivningar = _res(7700, 7899)
    avskrivningar_prev = _prev_res(7700, 7899)
    if avskrivningar or avskrivningar_prev:
        _add(CashFlowLine("Av- och nedskrivningar", avskrivningar, avskrivningar_prev, indent=2))

    # Unrealized exchange gains/losses etc. – typically small for consulting companies
    # Bokslutsdispositioner
    bokslut = _res(8800, 8899)
    bokslut_prev = _prev_res(8800, 8899)
    if bokslut or bokslut_prev:
        _add(CashFlowLine("Bokslutsdispositioner", bokslut, bokslut_prev, indent=2))

    # Tax paid (8900-8989)
    skatt = _res(8900, 8989)
    skatt_prev = _prev_res(8900, 8989)
    if skatt or skatt_prev:
        _add(CashFlowLine("Betald inkomstskatt", -skatt, -skatt_prev, indent=2))

    sum_before_wc = arets_resultat + avskrivningar + bokslut - skatt
    sum_before_wc_prev = arets_resultat_prev + avskrivningar_prev + bokslut_prev - skatt_prev

    # Working capital changes
    _add(CashFlowLine("Förändringar av rörelsekapital:", is_sum=True, indent=1))

    # Change in current receivables (1400-1799): increase = cash outflow
    fordringar_ub = _ub(1400, 1799)
    fordringar_ib = _ib(1400, 1799)
    delta_fordringar = -(fordringar_ub - fordringar_ib)

    fordringar_ub_prev = _ub_prev(1400, 1799)
    fordringar_ib_prev = _ib_prev(1400, 1799)
    delta_fordringar_prev = -(fordringar_ub_prev - fordringar_ib_prev)

    if delta_fordringar or delta_fordringar_prev:
        _add(CashFlowLine("Förändring av rörelsefordringar", delta_fordringar, delta_fordringar_prev, indent=2))

    # Change in current liabilities (2400-2999): increase = cash inflow
    skulder_ub = -_ub(2400, 2999)
    skulder_ib = -_ib(2400, 2999)
    delta_skulder = skulder_ub - skulder_ib

    skulder_ub_prev = -_ub_prev(2400, 2999)
    skulder_ib_prev = -_ib_prev(2400, 2999)
    delta_skulder_prev = skulder_ub_prev - skulder_ib_prev

    if delta_skulder or delta_skulder_prev:
        _add(CashFlowLine("Förändring av rörelseskulder", delta_skulder, delta_skulder_prev, indent=2))

    # Change in inventory (1400-1499 already in fordringar, separate if needed)
    varulager_ub = _ub(1400, 1499)
    varulager_ib = _ib(1400, 1499)
    delta_varulager = -(varulager_ub - varulager_ib)

    varulager_ub_prev = _ub_prev(1400, 1499)
    varulager_ib_prev = _ib_prev(1400, 1499)
    delta_varulager_prev = -(varulager_ub_prev - varulager_ib_prev)

    operating = sum_before_wc + delta_fordringar + delta_skulder
    operating_prev = sum_before_wc_prev + delta_fordringar_prev + delta_skulder_prev

    _add(CashFlowLine("Kassaflöde från den löpande verksamheten", operating, operating_prev, is_sum=True))

    # == INVESTERINGSVERKSAMHETEN ==
    _add(CashFlowLine("Investeringsverksamheten", is_sum=True))

    # Change in fixed assets (1000-1399): increase = investment outflow
    anl_ub = _ub(1000, 1399)
    anl_ib = _ib(1000, 1399)
    # We need to add back depreciation since it reduced the UB but isn't a cash flow
    delta_anl = -(anl_ub - anl_ib + avskrivningar)

    anl_ub_prev = _ub_prev(1000, 1399)
    anl_ib_prev = _ib_prev(1000, 1399)
    delta_anl_prev = -(anl_ub_prev - anl_ib_prev + avskrivningar_prev)

    if delta_anl or delta_anl_prev:
        _add(CashFlowLine("Förvärv av materiella anläggningstillgångar", delta_anl, delta_anl_prev, indent=1))

    # Short-term investments (1800-1899)
    plac_ub = _ub(1800, 1899)
    plac_ib = _ib(1800, 1899)
    delta_plac = -(plac_ub - plac_ib)

    plac_ub_prev = _ub_prev(1800, 1899)
    plac_ib_prev = _ib_prev(1800, 1899)
    delta_plac_prev = -(plac_ub_prev - plac_ib_prev)

    if delta_plac or delta_plac_prev:
        _add(CashFlowLine("Förändring av kortfristiga placeringar", delta_plac, delta_plac_prev, indent=1))

    investing = delta_anl + delta_plac
    investing_prev = delta_anl_prev + delta_plac_prev
    _add(CashFlowLine("Kassaflöde från investeringsverksamheten", investing, investing_prev, is_sum=True))

    # == FINANSIERINGSVERKSAMHETEN ==
    _add(CashFlowLine("Finansieringsverksamheten", is_sum=True))

    # Change in long-term debt (2300-2399)
    lang_ub = -_ub(2300, 2399)
    lang_ib = -_ib(2300, 2399)
    delta_lang = lang_ub - lang_ib

    lang_ub_prev = -_ub_prev(2300, 2399)
    lang_ib_prev = -_ib_prev(2300, 2399)
    delta_lang_prev = lang_ub_prev - lang_ib_prev

    if delta_lang or delta_lang_prev:
        _add(CashFlowLine("Förändring av långfristiga skulder", delta_lang, delta_lang_prev, indent=1))

    # Change in equity from transactions (new share capital, dividends, etc.)
    # Aktiekapital + överkursfond changes
    ek_ub = -_ub(2081, 2089)
    ek_ib = -_ib(2081, 2089)
    delta_ek = ek_ub - ek_ib

    ek_ub_prev = -_ub_prev(2081, 2089)
    ek_ib_prev = -_ib_prev(2081, 2089)
    delta_ek_prev = ek_ub_prev - ek_ib_prev

    if delta_ek or delta_ek_prev:
        _add(CashFlowLine("Nyemission", delta_ek, delta_ek_prev, indent=1))

    # Utdelning (account 2898 typically, or change in 2091/2098 minus årets resultat)
    # Simplified: check if fritt EK decreased beyond årets resultat
    # For now we don't have reliable dividend detection, so skip if zero

    financing = delta_lang + delta_ek
    financing_prev = delta_lang_prev + delta_ek_prev
    _add(CashFlowLine("Kassaflöde från finansieringsverksamheten", financing, financing_prev, is_sum=True))

    # == ÅRETS KASSAFLÖDE ==
    net = operating + investing + financing
    net_prev = operating_prev + investing_prev + financing_prev
    _add(CashFlowLine("Årets kassaflöde", net, net_prev, is_sum=True))

    # Likvida medel
    kassa_ib = _ib(1900, 1999)
    kassa_ib_prev = _ib_prev(1900, 1999)
    _add(CashFlowLine("Likvida medel vid årets början", kassa_ib, kassa_ib_prev))

    kassa_ub = _ub(1900, 1999)
    kassa_ub_prev = _ub_prev(1900, 1999)
    _add(CashFlowLine("Likvida medel vid årets slut", kassa_ub, kassa_ub_prev, is_sum=True))

    return cf
