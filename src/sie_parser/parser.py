"""SIE4 file parser.

Parses SIE4 files (Swedish standard for accounting data exchange) into
structured data models. Handles PC8 (CP437) encoding.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from .models import (
    Account,
    Balance,
    Company,
    Dimension,
    PeriodBalance,
    ResultRow,
    SieFile,
    Transaction,
    Voucher,
)

# SIE files use PC8 encoding (IBM Code Page 437)
SIE_ENCODING = "cp437"


def parse_sie_file(path: str | Path) -> SieFile:
    """Parse a SIE4 file and return a SieFile model."""
    path = Path(path)
    raw = path.read_bytes()
    text = raw.decode(SIE_ENCODING, errors="replace")
    lines = text.splitlines()
    return _parse_lines(lines)


def parse_sie_bytes(data: bytes) -> SieFile:
    """Parse SIE4 data from bytes (e.g. uploaded file)."""
    text = data.decode(SIE_ENCODING, errors="replace")
    lines = text.splitlines()
    return _parse_lines(lines)


def _parse_lines(lines: list[str]) -> SieFile:
    sie = SieFile()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("//"):
            i += 1
            continue

        if line.startswith("#VER"):
            voucher, i = _parse_voucher(lines, i)
            sie.vouchers.append(voucher)
            continue

        _parse_label(line, sie)
        i += 1

    return sie


def _parse_label(line: str, sie: SieFile) -> None:
    """Parse a single SIE label line."""
    tokens = _tokenize(line)
    if not tokens:
        return

    label = tokens[0].upper()

    if label == "#FLAGGA":
        sie.flag = _int(tokens, 1)
    elif label == "#FORMAT":
        sie.format = _str(tokens, 1)
    elif label == "#SIETYP":
        sie.sie_type = _int(tokens, 1)
    elif label == "#PROGRAM":
        sie.program = _str(tokens, 1)
        sie.program_version = _str(tokens, 2)
    elif label == "#GEN":
        sie.generated_date = _str(tokens, 1)
    elif label == "#FNR":
        sie.fnr = _str(tokens, 1)
    elif label == "#FNAMN":
        sie.company.name = _str(tokens, 1)
    elif label == "#ADRESS":
        sie.company.address_contact = _str(tokens, 1)
        sie.company.address_street = _str(tokens, 2)
        sie.company.address_postal = _str(tokens, 3)
        sie.company.address_phone = _str(tokens, 4)
    elif label == "#RAR":
        offset = _int(tokens, 1)
        start = _parse_date(_str(tokens, 2))
        end = _parse_date(_str(tokens, 3))
        if offset == 0:
            sie.company.fiscal_year_start = start
            sie.company.fiscal_year_end = end
    elif label == "#ORGNR":
        sie.company.org_number = _str(tokens, 1)
    elif label == "#OMFATTN":
        sie.coverage_date = _parse_date(_str(tokens, 1))
    elif label == "#KPTYP":
        sie.account_plan_type = _str(tokens, 1)
    elif label == "#KONTO":
        num = _str(tokens, 1)
        name = _str(tokens, 2)
        if num not in sie.accounts:
            sie.accounts[num] = Account(number=num, name=name)
        else:
            sie.accounts[num].name = name
    elif label == "#SRU":
        num = _str(tokens, 1)
        sru = _str(tokens, 2)
        if num in sie.accounts:
            sie.accounts[num].sru_code = sru
        else:
            sie.accounts[num] = Account(number=num, name="", sru_code=sru)
    elif label == "#DIM":
        dim_num = _int(tokens, 1)
        dim_name = _str(tokens, 2)
        sie.dimensions.append(Dimension(number=dim_num, name=dim_name))
    elif label == "#IB":
        sie.ib.append(Balance(
            year_offset=_int(tokens, 1),
            account=_str(tokens, 2),
            amount=_decimal(tokens, 3),
            quantity=_decimal(tokens, 4),
        ))
    elif label == "#UB":
        sie.ub.append(Balance(
            year_offset=_int(tokens, 1),
            account=_str(tokens, 2),
            amount=_decimal(tokens, 3),
            quantity=_decimal(tokens, 4),
        ))
    elif label == "#RES":
        sie.res.append(ResultRow(
            year_offset=_int(tokens, 1),
            account=_str(tokens, 2),
            amount=_decimal(tokens, 3),
            quantity=_decimal(tokens, 4),
        ))
    elif label == "#PSALDO":
        sie.psaldo.append(PeriodBalance(
            year_offset=_int(tokens, 1),
            period=_str(tokens, 2),
            account=_str(tokens, 3),
            object_id=_str(tokens, 4),
            amount=_decimal(tokens, 5),
            quantity=_decimal(tokens, 6),
        ))


def _parse_voucher(lines: list[str], start_idx: int) -> tuple[Voucher, int]:
    """Parse a #VER block with its #TRANS lines."""
    line = lines[start_idx].strip()
    tokens = _tokenize(line)

    voucher = Voucher(
        series=_str(tokens, 1),
        number=_str(tokens, 2),
        date=_str(tokens, 3),
        text=_str(tokens, 4),
        registration_date=_str(tokens, 5),
    )

    i = start_idx + 1
    # Find opening brace
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == "{":
            i += 1
            break
        i += 1

    # Parse transactions until closing brace
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == "}":
            i += 1
            break
        if stripped.startswith("#TRANS"):
            trans = _parse_transaction(stripped)
            voucher.transactions.append(trans)
        i += 1

    return voucher, i


def _parse_transaction(line: str) -> Transaction:
    """Parse a #TRANS line."""
    tokens = _tokenize(line)
    return Transaction(
        account=_str(tokens, 1),
        object_id=_str(tokens, 2),
        amount=_decimal(tokens, 3),
        date=_str(tokens, 4) or None,
        text=_str(tokens, 5),
        quantity=_decimal(tokens, 6),
    )


# --- Tokenizer ---

def _tokenize(line: str) -> list[str]:
    """Tokenize a SIE line, handling quoted strings and {} blocks."""
    tokens: list[str] = []
    i = 0
    n = len(line)
    while i < n:
        # Skip whitespace
        if line[i] in (" ", "\t"):
            i += 1
            continue
        # Quoted string
        if line[i] == '"':
            i += 1
            start = i
            while i < n and line[i] != '"':
                i += 1
            tokens.append(line[start:i])
            if i < n:
                i += 1  # skip closing quote
        # Curly brace block (object specifier like {})
        elif line[i] == '{':
            i += 1
            start = i
            while i < n and line[i] != '}':
                i += 1
            tokens.append(line[start:i].strip())
            if i < n:
                i += 1  # skip closing brace
        # Regular token
        else:
            start = i
            while i < n and line[i] not in (" ", "\t", '"', "{"):
                i += 1
            tokens.append(line[start:i])
    return tokens


# --- Helpers ---

def _str(tokens: list[str], idx: int) -> str:
    return tokens[idx] if idx < len(tokens) else ""


def _int(tokens: list[str], idx: int) -> int:
    s = _str(tokens, idx)
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0


def _decimal(tokens: list[str], idx: int) -> Decimal:
    s = _str(tokens, idx)
    if not s:
        return Decimal(0)
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal(0)


def _parse_date(s: str) -> Optional[date]:
    if not s or len(s) != 8:
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except (ValueError, TypeError):
        return None
