"""
Double-entry bookkeeping business logic for LedgerPro.
"""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Company, FiscalYear

from .models import Account, ExchangeRate, JournalEntry, JournalLine

logger = logging.getLogger(__name__)


class DoubleEntryError(Exception):
    """Raised when double-entry rules are violated."""
    pass


class FiscalPeriodError(Exception):
    """Raised when operations target a closed fiscal period."""
    pass


def generate_entry_number(company: Company) -> str:
    """Generate the next sequential journal entry number for a company."""
    last_entry = (
        JournalEntry.objects.filter(company=company)
        .order_by("-entry_number")
        .first()
    )
    if last_entry:
        try:
            prefix = "JE-"
            last_num = int(last_entry.entry_number.replace(prefix, ""))
            return f"{prefix}{last_num + 1:06d}"
        except (ValueError, AttributeError):
            pass

    return "JE-000001"


def validate_journal_lines(lines_data: List[dict]) -> None:
    """
    Validate journal entry lines for double-entry compliance.
    Raises DoubleEntryError if rules are violated.
    """
    if len(lines_data) < 2:
        raise DoubleEntryError(
            "A journal entry must have at least two lines."
        )

    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for line in lines_data:
        debit = Decimal(str(line.get("debit_amount", "0.00")))
        credit = Decimal(str(line.get("credit_amount", "0.00")))

        if debit < 0 or credit < 0:
            raise DoubleEntryError("Amounts cannot be negative.")

        if debit > 0 and credit > 0:
            raise DoubleEntryError(
                "A line cannot have both debit and credit amounts. "
                "Use separate lines instead."
            )

        if debit == 0 and credit == 0:
            raise DoubleEntryError(
                "Each line must have either a debit or credit amount."
            )

        total_debit += debit
        total_credit += credit

    if total_debit != total_credit:
        raise DoubleEntryError(
            f"Entry is not balanced. Total debits ({total_debit}) "
            f"must equal total credits ({total_credit})."
        )


def get_fiscal_year(company: Company, entry_date: date) -> Optional[FiscalYear]:
    """Find the fiscal year that contains the given date."""
    return FiscalYear.objects.filter(
        company=company,
        start_date__lte=entry_date,
        end_date__gte=entry_date,
    ).first()


@transaction.atomic
def create_journal_entry(
    company: Company,
    entry_date: date,
    description: str,
    lines_data: List[dict],
    created_by,
    entry_type: str = JournalEntry.EntryType.STANDARD,
    reference: str = "",
    currency: str = "USD",
    exchange_rate: Decimal = Decimal("1.000000"),
    source_module: str = "",
    source_id=None,
    auto_post: bool = False,
) -> JournalEntry:
    """
    Create a new journal entry with lines, enforcing double-entry rules.

    Args:
        company: The company this entry belongs to.
        entry_date: Date of the transaction.
        description: Memo / description.
        lines_data: List of dicts with keys: account_id, debit_amount, credit_amount, description.
        created_by: User creating the entry.
        entry_type: Type of journal entry.
        reference: External reference number.
        currency: Currency code.
        exchange_rate: Exchange rate to base currency.
        source_module: Originating module name.
        source_id: ID from source document.
        auto_post: If True, immediately post the entry.

    Returns:
        The created JournalEntry instance.

    Raises:
        DoubleEntryError: If double-entry rules are violated.
        FiscalPeriodError: If the target fiscal period is closed.
    """
    # Validate double-entry rules
    validate_journal_lines(lines_data)

    # Check fiscal year
    fiscal_year = get_fiscal_year(company, entry_date)
    if fiscal_year and fiscal_year.is_closed:
        raise FiscalPeriodError(
            f"Fiscal year {fiscal_year.name} is closed. "
            "No entries can be posted to this period."
        )

    # Generate entry number
    entry_number = generate_entry_number(company)

    # Create the journal entry
    entry = JournalEntry.objects.create(
        company=company,
        entry_number=entry_number,
        date=entry_date,
        description=description,
        reference=reference,
        entry_type=entry_type,
        status=JournalEntry.Status.DRAFT,
        fiscal_year=fiscal_year,
        currency=currency,
        exchange_rate=exchange_rate,
        source_module=source_module,
        source_id=source_id,
        created_by=created_by,
    )

    # Create journal lines
    for line_data in lines_data:
        account = Account.objects.get(
            id=line_data["account_id"],
            company=company,
        )
        JournalLine.objects.create(
            journal_entry=entry,
            account=account,
            description=line_data.get("description", ""),
            debit_amount=Decimal(str(line_data.get("debit_amount", "0.00"))),
            credit_amount=Decimal(str(line_data.get("credit_amount", "0.00"))),
            currency=currency,
            exchange_rate=exchange_rate,
            tax_rate_id=line_data.get("tax_rate_id"),
            tax_amount=Decimal(str(line_data.get("tax_amount", "0.00"))),
        )

    if auto_post:
        post_journal_entry(entry, created_by)

    logger.info(
        "Created journal entry %s for company %s (%.2f total)",
        entry.entry_number, company.name, entry.total_debit,
    )

    return entry


@transaction.atomic
def post_journal_entry(entry: JournalEntry, approved_by) -> JournalEntry:
    """
    Post a journal entry, updating account balances.
    Once posted, an entry cannot be directly edited -- only voided/reversed.
    """
    if entry.status == JournalEntry.Status.POSTED:
        raise DoubleEntryError("This entry is already posted.")

    if entry.status == JournalEntry.Status.VOIDED:
        raise DoubleEntryError("Cannot post a voided entry.")

    if not entry.is_balanced:
        raise DoubleEntryError(
            "Cannot post an unbalanced entry. "
            f"Debits: {entry.total_debit}, Credits: {entry.total_credit}"
        )

    # Check fiscal year
    if entry.fiscal_year and entry.fiscal_year.is_closed:
        raise FiscalPeriodError("Cannot post to a closed fiscal period.")

    # Update account balances
    for line in entry.lines.select_related("account"):
        account = line.account
        if account.normal_balance == "debit":
            account.current_balance += line.base_debit_amount - line.base_credit_amount
        else:
            account.current_balance += line.base_credit_amount - line.base_debit_amount
        account.save(update_fields=["current_balance"])

    entry.status = JournalEntry.Status.POSTED
    entry.approved_by = approved_by
    entry.posted_at = timezone.now()
    entry.save(update_fields=["status", "approved_by", "posted_at"])

    logger.info("Posted journal entry %s", entry.entry_number)
    return entry


@transaction.atomic
def void_journal_entry(entry: JournalEntry, voided_by) -> JournalEntry:
    """
    Void a posted journal entry, reversing its effect on account balances.
    """
    if entry.status != JournalEntry.Status.POSTED:
        raise DoubleEntryError("Only posted entries can be voided.")

    # Reverse account balance effects
    for line in entry.lines.select_related("account"):
        account = line.account
        if account.normal_balance == "debit":
            account.current_balance -= line.base_debit_amount - line.base_credit_amount
        else:
            account.current_balance -= line.base_credit_amount - line.base_debit_amount
        account.save(update_fields=["current_balance"])

    entry.status = JournalEntry.Status.VOIDED
    entry.save(update_fields=["status"])

    logger.info("Voided journal entry %s by %s", entry.entry_number, voided_by.email)
    return entry


@transaction.atomic
def reverse_journal_entry(
    entry: JournalEntry,
    reversal_date: date,
    created_by,
) -> JournalEntry:
    """
    Create a reversing entry for a posted journal entry.
    Swaps debits and credits on the original entry.
    """
    if entry.status != JournalEntry.Status.POSTED:
        raise DoubleEntryError("Only posted entries can be reversed.")

    lines_data = []
    for line in entry.lines.all():
        lines_data.append({
            "account_id": str(line.account_id),
            "debit_amount": str(line.credit_amount),
            "credit_amount": str(line.debit_amount),
            "description": f"Reversal: {line.description}",
        })

    reversal = create_journal_entry(
        company=entry.company,
        entry_date=reversal_date,
        description=f"Reversal of {entry.entry_number}: {entry.description}",
        lines_data=lines_data,
        created_by=created_by,
        entry_type=JournalEntry.EntryType.REVERSING,
        reference=entry.entry_number,
        currency=entry.currency,
        exchange_rate=entry.exchange_rate,
        auto_post=True,
    )

    entry.reversing_entry = reversal
    entry.save(update_fields=["reversing_entry"])

    logger.info(
        "Reversed journal entry %s with %s",
        entry.entry_number, reversal.entry_number,
    )
    return reversal


def get_account_balance(
    account: Account,
    as_of_date: Optional[date] = None,
    start_date: Optional[date] = None,
) -> Decimal:
    """
    Calculate the balance for an account, optionally for a date range.
    """
    lines = JournalLine.objects.filter(
        account=account,
        journal_entry__status=JournalEntry.Status.POSTED,
    )

    if start_date:
        lines = lines.filter(journal_entry__date__gte=start_date)
    if as_of_date:
        lines = lines.filter(journal_entry__date__lte=as_of_date)

    from django.db.models import Sum

    totals = lines.aggregate(
        total_debit=Sum("base_debit_amount"),
        total_credit=Sum("base_credit_amount"),
    )

    debit = totals["total_debit"] or Decimal("0.00")
    credit = totals["total_credit"] or Decimal("0.00")

    if account.normal_balance == "debit":
        balance = account.opening_balance + debit - credit
    else:
        balance = account.opening_balance + credit - debit

    return balance


def get_trial_balance(company: Company, as_of_date: date) -> list:
    """
    Generate a trial balance for all accounts in the company.
    Returns a list of dicts with account info and debit/credit balances.
    """
    from django.db.models import Sum

    accounts = Account.objects.filter(
        company=company, is_active=True
    ).order_by("code")

    trial_balance = []
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for account in accounts:
        lines = JournalLine.objects.filter(
            account=account,
            journal_entry__status=JournalEntry.Status.POSTED,
            journal_entry__date__lte=as_of_date,
        )

        totals = lines.aggregate(
            debit=Sum("base_debit_amount"),
            credit=Sum("base_credit_amount"),
        )
        debit = (totals["debit"] or Decimal("0.00")) + (
            account.opening_balance if account.normal_balance == "debit" else Decimal("0.00")
        )
        credit = (totals["credit"] or Decimal("0.00")) + (
            account.opening_balance if account.normal_balance == "credit" else Decimal("0.00")
        )

        net = debit - credit
        row = {
            "account_id": str(account.id),
            "account_code": account.code,
            "account_name": account.name,
            "account_type": account.account_type,
            "debit_balance": max(net, Decimal("0.00")),
            "credit_balance": max(-net, Decimal("0.00")),
        }
        trial_balance.append(row)
        total_debit += row["debit_balance"]
        total_credit += row["credit_balance"]

    return {
        "as_of_date": as_of_date.isoformat(),
        "accounts": trial_balance,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "is_balanced": total_debit == total_credit,
    }
