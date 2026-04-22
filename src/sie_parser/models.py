"""Data models for SIE4 file format."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass
class Company:
    name: str = ""
    org_number: str = ""
    address_contact: str = ""
    address_street: str = ""
    address_postal: str = ""
    address_phone: str = ""
    fiscal_year_start: Optional[date] = None
    fiscal_year_end: Optional[date] = None
    prev_fiscal_year_start: Optional[date] = None
    prev_fiscal_year_end: Optional[date] = None


@dataclass
class Account:
    number: str
    name: str
    sru_code: Optional[str] = None


@dataclass
class Balance:
    """Ingående (IB) or utgående (UB) balance for an account."""
    year_offset: int  # 0 = current year, -1 = previous year, etc.
    account: str
    amount: Decimal = Decimal(0)
    quantity: Decimal = Decimal(0)


@dataclass
class ResultRow:
    """Annual result row (#RES) for an account."""
    year_offset: int
    account: str
    amount: Decimal = Decimal(0)
    quantity: Decimal = Decimal(0)


@dataclass
class PeriodBalance:
    """Period balance (#PSALDO) for an account in a specific month."""
    year_offset: int
    period: str  # YYYYMM
    account: str
    object_id: str = ""
    amount: Decimal = Decimal(0)
    quantity: Decimal = Decimal(0)


@dataclass
class Dimension:
    number: int
    name: str


@dataclass
class Transaction:
    account: str
    object_id: str = ""
    amount: Decimal = Decimal(0)
    date: Optional[str] = None
    text: str = ""
    quantity: Decimal = Decimal(0)


@dataclass
class Voucher:
    series: str
    number: str
    date: str  # YYYYMMDD
    text: str = ""
    registration_date: str = ""
    transactions: list[Transaction] = field(default_factory=list)


@dataclass
class SieFile:
    """Root model containing all parsed SIE4 data."""
    # Metadata
    flag: int = 0
    format: str = "PC8"
    sie_type: int = 4
    program: str = ""
    program_version: str = ""
    generated_date: str = ""
    fnr: str = ""

    # Company info
    company: Company = field(default_factory=Company)

    # Chart of accounts type
    account_plan_type: str = ""

    # Coverage date
    coverage_date: Optional[date] = None

    # Accounts: number -> Account
    accounts: dict[str, Account] = field(default_factory=dict)

    # Dimensions
    dimensions: list[Dimension] = field(default_factory=list)

    # Balances
    ib: list[Balance] = field(default_factory=list)  # Ingående balans
    ub: list[Balance] = field(default_factory=list)  # Utgående balans

    # Results
    res: list[ResultRow] = field(default_factory=list)

    # Period balances
    psaldo: list[PeriodBalance] = field(default_factory=list)

    # Vouchers
    vouchers: list[Voucher] = field(default_factory=list)

    def get_ub(self, account: str, year_offset: int = 0) -> Decimal:
        """Get the closing balance for an account."""
        for b in self.ub:
            if b.account == account and b.year_offset == year_offset:
                return b.amount
        return Decimal(0)

    def get_ib(self, account: str, year_offset: int = 0) -> Decimal:
        """Get the opening balance for an account."""
        for b in self.ib:
            if b.account == account and b.year_offset == year_offset:
                return b.amount
        return Decimal(0)

    def get_result(self, account: str, year_offset: int = 0) -> Decimal:
        """Get the annual result for an account."""
        for r in self.res:
            if r.account == account and r.year_offset == year_offset:
                return r.amount
        return Decimal(0)

    def accounts_in_range(self, start: int, end: int) -> list[Account]:
        """Get all accounts with numbers in [start, end]."""
        result = []
        for num, acct in self.accounts.items():
            try:
                n = int(num)
                if start <= n <= end:
                    result.append(acct)
            except ValueError:
                continue
        return sorted(result, key=lambda a: a.number)

    def sum_ub_range(self, start: int, end: int, year_offset: int = 0) -> Decimal:
        """Sum closing balances for accounts in [start, end]."""
        total = Decimal(0)
        for acct in self.accounts_in_range(start, end):
            total += self.get_ub(acct.number, year_offset)
        return total

    def sum_result_range(self, start: int, end: int, year_offset: int = 0) -> Decimal:
        """Sum result rows for accounts in [start, end]."""
        total = Decimal(0)
        for acct in self.accounts_in_range(start, end):
            total += self.get_result(acct.number, year_offset)
        return total

    @property
    def has_previous_year(self) -> bool:
        """Check if there is data for the previous fiscal year."""
        return self.company.prev_fiscal_year_end is not None
