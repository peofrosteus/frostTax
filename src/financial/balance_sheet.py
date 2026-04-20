"""Balance sheet (Balansräkning) generation.

Generates a balance sheet following K2/K3 structure based on UB (closing balances).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from src.sie_parser.models import SieFile


@dataclass
class LineItem:
    label: str
    amount: Decimal = Decimal(0)
    previous_amount: Decimal = Decimal(0)
    note: str = ""
    is_sum: bool = False
    indent: int = 0


@dataclass
class BalanceSheet:
    assets: list[LineItem] = field(default_factory=list)
    equity_and_liabilities: list[LineItem] = field(default_factory=list)

    @property
    def total_assets(self) -> Decimal:
        return self._find(self.assets, "SUMMA TILLGÅNGAR")

    @property
    def total_equity_and_liabilities(self) -> Decimal:
        return self._find(self.equity_and_liabilities, "SUMMA EGET KAPITAL OCH SKULDER")

    @property
    def is_balanced(self) -> bool:
        return self.total_assets == -self.total_equity_and_liabilities

    def _find(self, items: list[LineItem], label: str) -> Decimal:
        for li in items:
            if li.label == label:
                return li.amount
        return Decimal(0)


def generate_balance_sheet(
    sie: SieFile,
    year_offset: int = 0,
    framework: str = "K2",
) -> BalanceSheet:
    """Generate a balance sheet from SIE data.

    In SIE, asset accounts (1xxx) have positive balances (debit).
    Equity/liability accounts (2xxx) have negative balances (credit).
    We present assets as positive and equity/liabilities as positive
    (by negating the credit balances).
    """
    bs = BalanceSheet()

    def _ub(start: int, end: int) -> Decimal:
        return sie.sum_ub_range(start, end, year_offset)

    def _prev(start: int, end: int) -> Decimal:
        return sie.sum_ub_range(start, end, year_offset - 1)

    # ===== TILLGÅNGAR (ASSETS) =====
    _a = bs.assets.append

    # --- Anläggningstillgångar ---
    immateriella = _ub(1000, 1099)
    immateriella_prev = _prev(1000, 1099)

    byggnader_mark = _ub(1100, 1199)
    byggnader_mark_prev = _prev(1100, 1199)

    maskiner_inventarier = _ub(1200, 1299)
    maskiner_inventarier_prev = _prev(1200, 1299)

    materiella = byggnader_mark + maskiner_inventarier
    materiella_prev = byggnader_mark_prev + maskiner_inventarier_prev

    finansiella_anl = _ub(1300, 1399)
    finansiella_anl_prev = _prev(1300, 1399)

    sum_anlaggningstillgangar = immateriella + materiella + finansiella_anl
    sum_anlaggningstillgangar_prev = immateriella_prev + materiella_prev + finansiella_anl_prev

    # --- Omsättningstillgångar ---
    varulager = _ub(1400, 1499)
    varulager_prev = _prev(1400, 1499)

    kundfordringar = _ub(1500, 1599)
    kundfordringar_prev = _prev(1500, 1599)

    ovriga_kortfristiga_fordringar = _ub(1600, 1799)
    ovriga_kortfristiga_fordringar_prev = _prev(1600, 1799)

    kortfristiga_fordringar = kundfordringar + ovriga_kortfristiga_fordringar
    kortfristiga_fordringar_prev = kundfordringar_prev + ovriga_kortfristiga_fordringar_prev

    kortfristiga_placeringar = _ub(1800, 1899)
    kortfristiga_placeringar_prev = _prev(1800, 1899)

    kassa_bank = _ub(1900, 1999)
    kassa_bank_prev = _prev(1900, 1999)

    sum_omsattningstillgangar = (
        varulager + kortfristiga_fordringar + kortfristiga_placeringar + kassa_bank
    )
    sum_omsattningstillgangar_prev = (
        varulager_prev + kortfristiga_fordringar_prev
        + kortfristiga_placeringar_prev + kassa_bank_prev
    )

    sum_tillgangar = sum_anlaggningstillgangar + sum_omsattningstillgangar
    sum_tillgangar_prev = sum_anlaggningstillgangar_prev + sum_omsattningstillgangar_prev

    # Build asset lines
    _a(LineItem("Anläggningstillgångar", is_sum=True))

    if immateriella:
        _a(LineItem("Immateriella anläggningstillgångar", is_sum=True, indent=1))
        _a(LineItem("Balanserade utgifter för utvecklingsarbeten", immateriella, immateriella_prev, indent=2))

    if materiella:
        _a(LineItem("Materiella anläggningstillgångar", is_sum=True, indent=1))
        if byggnader_mark:
            _a(LineItem("Byggnader och mark", byggnader_mark, byggnader_mark_prev, indent=2))
        if maskiner_inventarier:
            _a(LineItem("Inventarier, verktyg och installationer", maskiner_inventarier, maskiner_inventarier_prev, indent=2))

    if finansiella_anl:
        _a(LineItem("Finansiella anläggningstillgångar", is_sum=True, indent=1))
        _a(LineItem("Andra långfristiga fordringar", finansiella_anl, finansiella_anl_prev, indent=2))

    if sum_anlaggningstillgangar:
        _a(LineItem("Summa anläggningstillgångar", sum_anlaggningstillgangar, sum_anlaggningstillgangar_prev, is_sum=True))

    _a(LineItem("Omsättningstillgångar", is_sum=True))

    if varulager:
        _a(LineItem("Varulager m.m.", varulager, varulager_prev, indent=1))

    if kortfristiga_fordringar:
        _a(LineItem("Kortfristiga fordringar", is_sum=True, indent=1))
        if kundfordringar:
            _a(LineItem("Kundfordringar", kundfordringar, kundfordringar_prev, indent=2))
        if ovriga_kortfristiga_fordringar:
            _a(LineItem("Övriga fordringar", ovriga_kortfristiga_fordringar, ovriga_kortfristiga_fordringar_prev, indent=2))
        _a(LineItem("Summa kortfristiga fordringar", kortfristiga_fordringar, kortfristiga_fordringar_prev, is_sum=True, indent=1))

    if kortfristiga_placeringar:
        _a(LineItem("Kortfristiga placeringar", kortfristiga_placeringar, kortfristiga_placeringar_prev, indent=1))

    _a(LineItem("Kassa och bank", kassa_bank, kassa_bank_prev, indent=1))

    _a(LineItem("Summa omsättningstillgångar", sum_omsattningstillgangar, sum_omsattningstillgangar_prev, is_sum=True))
    _a(LineItem("SUMMA TILLGÅNGAR", sum_tillgangar, sum_tillgangar_prev, is_sum=True))

    # ===== EGET KAPITAL OCH SKULDER =====
    _e = bs.equity_and_liabilities.append

    # Equity accounts are negative (credit) in SIE – negate to show positive
    bundet_eget_kapital_aktiekapital = -_ub(2081, 2081)
    bundet_eget_kapital_aktiekapital_prev = -_prev(2081, 2081)

    uppskrivningsfond = -_ub(2085, 2085)
    uppskrivningsfond_prev = -_prev(2085, 2085)

    reservfond = -_ub(2086, 2086)
    reservfond_prev = -_prev(2086, 2086)

    sum_bundet = bundet_eget_kapital_aktiekapital + uppskrivningsfond + reservfond
    sum_bundet_prev = bundet_eget_kapital_aktiekapital_prev + uppskrivningsfond_prev + reservfond_prev

    # Fritt eget kapital
    balanserat_resultat = -_ub(2091, 2091) + (-_ub(2098, 2098))
    balanserat_resultat_prev = -_prev(2091, 2091) + (-_prev(2098, 2098))

    fritt_eget_kapital_ovrigt = -_ub(2090, 2090)
    fritt_eget_kapital_ovrigt_prev = -_prev(2090, 2090)

    arets_resultat = -_ub(2099, 2099)
    arets_resultat_prev = -_prev(2099, 2099)

    # If årets resultat is not booked on 2099, calculate from income statement
    if arets_resultat == 0:
        from src.financial.income_statement import generate_income_statement
        income_stmt = generate_income_statement(sie, year_offset)
        arets_resultat = income_stmt.annual_result

    sum_fritt = balanserat_resultat + fritt_eget_kapital_ovrigt + arets_resultat
    sum_fritt_prev = balanserat_resultat_prev + fritt_eget_kapital_ovrigt_prev + arets_resultat_prev

    sum_eget_kapital = sum_bundet + sum_fritt
    sum_eget_kapital_prev = sum_bundet_prev + sum_fritt_prev

    # Obeskattade reserver
    obeskattade_reserver = -_ub(2100, 2199)
    obeskattade_reserver_prev = -_prev(2100, 2199)

    # Avsättningar
    avsattningar = -_ub(2200, 2299)
    avsattningar_prev = -_prev(2200, 2299)

    # Långfristiga skulder
    langfristiga_skulder = -_ub(2300, 2399)
    langfristiga_skulder_prev = -_prev(2300, 2399)

    # Kortfristiga skulder
    leverantorsskulder = -_ub(2440, 2440)
    leverantorsskulder_prev = -_prev(2440, 2440)

    skatteskulder = -_ub(2500, 2599)
    skatteskulder_prev = -_prev(2500, 2599)

    ovriga_kortfristiga_skulder = -(
        _ub(2400, 2439) + _ub(2441, 2499)
        + _ub(2600, 2999)
    )
    ovriga_kortfristiga_skulder_prev = -(
        _prev(2400, 2439) + _prev(2441, 2499)
        + _prev(2600, 2999)
    )

    sum_kortfristiga_skulder = leverantorsskulder + skatteskulder + ovriga_kortfristiga_skulder
    sum_kortfristiga_skulder_prev = leverantorsskulder_prev + skatteskulder_prev + ovriga_kortfristiga_skulder_prev

    sum_ek_skulder = (
        sum_eget_kapital + obeskattade_reserver + avsattningar
        + langfristiga_skulder + sum_kortfristiga_skulder
    )
    sum_ek_skulder_prev = (
        sum_eget_kapital_prev + obeskattade_reserver_prev + avsattningar_prev
        + langfristiga_skulder_prev + sum_kortfristiga_skulder_prev
    )

    # Build equity & liabilities lines
    _e(LineItem("Eget kapital", is_sum=True))
    _e(LineItem("Bundet eget kapital", is_sum=True, indent=1))
    _e(LineItem("Aktiekapital", bundet_eget_kapital_aktiekapital, bundet_eget_kapital_aktiekapital_prev, indent=2))
    if uppskrivningsfond:
        _e(LineItem("Uppskrivningsfond", uppskrivningsfond, uppskrivningsfond_prev, indent=2))
    if reservfond:
        _e(LineItem("Reservfond", reservfond, reservfond_prev, indent=2))
    _e(LineItem("Summa bundet eget kapital", sum_bundet, sum_bundet_prev, is_sum=True, indent=1))

    _e(LineItem("Fritt eget kapital", is_sum=True, indent=1))
    if balanserat_resultat or fritt_eget_kapital_ovrigt:
        _e(LineItem(
            "Balanserat resultat",
            balanserat_resultat + fritt_eget_kapital_ovrigt,
            balanserat_resultat_prev + fritt_eget_kapital_ovrigt_prev,
            indent=2,
        ))
    _e(LineItem("Årets resultat", arets_resultat, arets_resultat_prev, indent=2))
    _e(LineItem("Summa fritt eget kapital", sum_fritt, sum_fritt_prev, is_sum=True, indent=1))
    _e(LineItem("Summa eget kapital", sum_eget_kapital, sum_eget_kapital_prev, is_sum=True))

    if obeskattade_reserver:
        _e(LineItem("Obeskattade reserver", obeskattade_reserver, obeskattade_reserver_prev))

    if avsattningar:
        _e(LineItem("Avsättningar", avsattningar, avsattningar_prev))

    if langfristiga_skulder:
        _e(LineItem("Långfristiga skulder", is_sum=True))
        _e(LineItem("Skulder till kreditinstitut", langfristiga_skulder, langfristiga_skulder_prev, indent=1))

    _e(LineItem("Kortfristiga skulder", is_sum=True))
    if leverantorsskulder:
        _e(LineItem("Leverantörsskulder", leverantorsskulder, leverantorsskulder_prev, indent=1))
    if skatteskulder:
        _e(LineItem("Skatteskulder", skatteskulder, skatteskulder_prev, indent=1))
    if ovriga_kortfristiga_skulder:
        _e(LineItem("Övriga kortfristiga skulder", ovriga_kortfristiga_skulder, ovriga_kortfristiga_skulder_prev, indent=1))
    _e(LineItem("Summa kortfristiga skulder", sum_kortfristiga_skulder, sum_kortfristiga_skulder_prev, is_sum=True))

    _e(LineItem("SUMMA EGET KAPITAL OCH SKULDER", sum_ek_skulder, sum_ek_skulder_prev, is_sum=True))

    return bs
