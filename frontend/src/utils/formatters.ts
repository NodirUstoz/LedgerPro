/**
 * Formatting utilities for dates, currency, and accounting display.
 */

/**
 * Format a number as currency.
 */
export function formatCurrency(
  value: string | number,
  currency = 'USD',
  locale = 'en-US',
): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '$0.00';
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

/**
 * Format a date string to a human-readable format.
 */
export function formatDate(
  dateStr: string | null | undefined,
  format: 'short' | 'long' | 'iso' = 'short',
): string {
  if (!dateStr) return '--';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;

  switch (format) {
    case 'long':
      return d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    case 'iso':
      return d.toISOString().split('T')[0];
    default:
      return d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
  }
}

/**
 * Format a number with commas and fixed decimal places.
 */
export function formatNumber(value: string | number, decimals = 2): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '0.00';
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format a percentage.
 */
export function formatPercent(value: string | number, decimals = 2): string {
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '0%';
  return `${num.toFixed(decimals)}%`;
}

/**
 * Get a human-readable label for an account type.
 */
export function accountTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    asset: 'Assets',
    liability: 'Liabilities',
    equity: 'Equity',
    revenue: 'Revenue',
    expense: 'Expenses',
  };
  return labels[type] || type;
}

/**
 * Get a CSS class for an invoice/expense status badge.
 */
export function statusColor(status: string): string {
  const colors: Record<string, string> = {
    draft: 'bg-gray-100 text-gray-700',
    pending: 'bg-yellow-100 text-yellow-800',
    approved: 'bg-blue-100 text-blue-800',
    posted: 'bg-green-100 text-green-800',
    sent: 'bg-blue-100 text-blue-800',
    paid: 'bg-green-100 text-green-800',
    partially_paid: 'bg-teal-100 text-teal-800',
    overdue: 'bg-red-100 text-red-800',
    voided: 'bg-gray-200 text-gray-500',
    rejected: 'bg-red-100 text-red-700',
    filed: 'bg-green-100 text-green-800',
    calculated: 'bg-indigo-100 text-indigo-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-700';
}

/**
 * Truncate a string to a max length, appending "..." if truncated.
 */
export function truncate(str: string, maxLength = 50): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - 3) + '...';
}
