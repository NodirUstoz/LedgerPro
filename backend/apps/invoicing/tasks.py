"""
Celery tasks for invoicing app.
"""

import logging
from datetime import date

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_overdue_invoices(self):
    """
    Check for invoices past their due date and update status to overdue.
    Runs daily via Celery Beat.
    """
    from .models import Invoice

    today = date.today()
    overdue_invoices = Invoice.objects.filter(
        due_date__lt=today,
        status__in=[Invoice.Status.SENT, Invoice.Status.PARTIALLY_PAID],
    )

    count = overdue_invoices.update(status=Invoice.Status.OVERDUE)
    logger.info("Marked %d invoices as overdue.", count)
    return {"overdue_count": count}


@shared_task(bind=True, max_retries=3)
def generate_recurring_invoices(self):
    """
    Generate invoices for recurring billing schedules.
    This is a placeholder for recurring invoice logic.
    """
    logger.info("Recurring invoice generation task executed.")
    return {"generated": 0}


@shared_task(bind=True, max_retries=3)
def send_invoice_email(self, invoice_id):
    """
    Send an invoice to the customer via email.
    """
    from django.core.mail import send_mail
    from django.conf import settings

    from .models import Invoice

    try:
        invoice = Invoice.objects.select_related("customer", "company").get(id=invoice_id)
    except Invoice.DoesNotExist:
        logger.error("Invoice %s not found.", invoice_id)
        return

    if not invoice.customer.email:
        logger.warning("Customer %s has no email.", invoice.customer.name)
        return

    subject = f"Invoice {invoice.invoice_number} from {invoice.company.name}"
    message = (
        f"Dear {invoice.customer.name},\n\n"
        f"Please find attached Invoice {invoice.invoice_number} "
        f"for {invoice.currency} {invoice.total_amount}.\n\n"
        f"Due Date: {invoice.due_date}\n\n"
        f"Thank you for your business.\n\n"
        f"Best regards,\n{invoice.company.name}"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invoice.customer.email],
            fail_silently=False,
        )
        logger.info(
            "Invoice %s emailed to %s.",
            invoice.invoice_number, invoice.customer.email,
        )
    except Exception as exc:
        logger.error("Failed to send invoice email: %s", exc)
        self.retry(exc=exc, countdown=60)


@shared_task(bind=True)
def send_payment_reminder(self, invoice_id):
    """
    Send a payment reminder for an overdue invoice.
    """
    from django.core.mail import send_mail
    from django.conf import settings

    from .models import Invoice

    try:
        invoice = Invoice.objects.select_related("customer", "company").get(id=invoice_id)
    except Invoice.DoesNotExist:
        logger.error("Invoice %s not found.", invoice_id)
        return

    if invoice.status != Invoice.Status.OVERDUE:
        return

    if not invoice.customer.email:
        return

    days_overdue = (date.today() - invoice.due_date).days
    subject = f"Payment Reminder: Invoice {invoice.invoice_number}"
    message = (
        f"Dear {invoice.customer.name},\n\n"
        f"This is a reminder that Invoice {invoice.invoice_number} "
        f"for {invoice.currency} {invoice.balance_due} is {days_overdue} days overdue.\n\n"
        f"Original Due Date: {invoice.due_date}\n"
        f"Balance Due: {invoice.currency} {invoice.balance_due}\n\n"
        f"Please arrange payment at your earliest convenience.\n\n"
        f"Best regards,\n{invoice.company.name}"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[invoice.customer.email],
            fail_silently=False,
        )
        logger.info("Payment reminder sent for invoice %s.", invoice.invoice_number)
    except Exception as exc:
        logger.error("Failed to send payment reminder: %s", exc)
