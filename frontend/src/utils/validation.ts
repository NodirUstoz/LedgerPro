/**
 * Validation helpers for forms across the LedgerPro frontend.
 */

/**
 * Validate that debit and credit totals are balanced.
 */
export function validateJournalBalance(
  lines: Array<{ debit_amount: string; credit_amount: string }>,
): { valid: boolean; totalDebit: number; totalCredit: number; difference: number } {
  let totalDebit = 0;
  let totalCredit = 0;

  for (const line of lines) {
    totalDebit += parseFloat(line.debit_amount) || 0;
    totalCredit += parseFloat(line.credit_amount) || 0;
  }

  const difference = Math.abs(totalDebit - totalCredit);
  return {
    valid: difference < 0.005, // tolerance for floating-point
    totalDebit,
    totalCredit,
    difference,
  };
}

/**
 * Validate that a line has either debit or credit, but not both.
 */
export function validateJournalLine(line: {
  debit_amount: string;
  credit_amount: string;
  account: string;
}): string[] {
  const errors: string[] = [];
  const debit = parseFloat(line.debit_amount) || 0;
  const credit = parseFloat(line.credit_amount) || 0;

  if (!line.account) {
    errors.push('Account is required.');
  }
  if (debit > 0 && credit > 0) {
    errors.push('A line cannot have both debit and credit amounts.');
  }
  if (debit === 0 && credit === 0) {
    errors.push('A line must have either a debit or credit amount.');
  }
  if (debit < 0 || credit < 0) {
    errors.push('Amounts cannot be negative.');
  }

  return errors;
}

/**
 * Validate an email address format.
 */
export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * Validate a required string field.
 */
export function isRequired(value: string | null | undefined, fieldName = 'Field'): string | null {
  if (!value || value.trim() === '') {
    return `${fieldName} is required.`;
  }
  return null;
}

/**
 * Validate that a date string is in ISO format (YYYY-MM-DD).
 */
export function isValidDate(dateStr: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return false;
  const d = new Date(dateStr);
  return !isNaN(d.getTime());
}

/**
 * Validate a positive decimal amount.
 */
export function isPositiveAmount(value: string | number): boolean {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  return !isNaN(num) && num > 0;
}

/**
 * Validate invoice line items before submission.
 */
export function validateInvoiceLines(
  lines: Array<{
    description: string;
    quantity: string;
    unit_price: string;
  }>,
): string[] {
  const errors: string[] = [];

  if (lines.length === 0) {
    errors.push('At least one line item is required.');
    return errors;
  }

  lines.forEach((line, idx) => {
    if (!line.description.trim()) {
      errors.push(`Line ${idx + 1}: Description is required.`);
    }
    const qty = parseFloat(line.quantity);
    if (isNaN(qty) || qty <= 0) {
      errors.push(`Line ${idx + 1}: Quantity must be greater than zero.`);
    }
    const price = parseFloat(line.unit_price);
    if (isNaN(price) || price < 0) {
      errors.push(`Line ${idx + 1}: Unit price cannot be negative.`);
    }
  });

  return errors;
}
