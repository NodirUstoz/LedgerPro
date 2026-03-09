/**
 * Custom hooks for common accounting operations.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import { fetchAccounts, fetchJournalEntries } from '../store/ledgerSlice';
import { fetchExpenses, fetchExpenseSummary } from '../store/expenseSlice';
import { fetchInvoices, fetchInvoiceSummary } from '../store/invoiceSlice';
import { fetchTaxRates } from '../store/taxSlice';

/**
 * Hook for loading and filtering chart of accounts.
 */
export function useChartOfAccounts(companyId: string | null) {
  const dispatch = useAppDispatch();
  const { accounts, accountsLoading } = useAppSelector((s) => s.ledger);
  const [typeFilter, setTypeFilter] = useState<string>('');

  useEffect(() => {
    if (companyId) {
      const params: Record<string, string> = { company: companyId };
      if (typeFilter) params.type = typeFilter;
      dispatch(fetchAccounts(params));
    }
  }, [dispatch, companyId, typeFilter]);

  const grouped = useMemo(() => {
    const groups: Record<string, typeof accounts> = {};
    for (const acct of accounts) {
      const type = acct.account_type;
      if (!groups[type]) groups[type] = [];
      groups[type].push(acct);
    }
    return groups;
  }, [accounts]);

  return { accounts, grouped, accountsLoading, typeFilter, setTypeFilter };
}

/**
 * Hook for dashboard summary data across all modules.
 */
export function useDashboardData(companyId: string | null) {
  const dispatch = useAppDispatch();
  const invoiceSummary = useAppSelector((s) => s.invoices.summary);
  const expenseSummary = useAppSelector((s) => s.expenses.summary);
  const [isLoading, setIsLoading] = useState(false);

  const refresh = useCallback(() => {
    if (!companyId) return;
    setIsLoading(true);
    const today = new Date().toISOString().split('T')[0];
    const yearStart = `${new Date().getFullYear()}-01-01`;

    Promise.all([
      dispatch(fetchInvoiceSummary(companyId)),
      dispatch(fetchExpenseSummary({ company: companyId, start_date: yearStart, end_date: today })),
    ]).finally(() => setIsLoading(false));
  }, [dispatch, companyId]);

  useEffect(() => { refresh(); }, [refresh]);

  return { invoiceSummary, expenseSummary, isLoading, refresh };
}

/**
 * Hook for formatting currency values consistently.
 */
export function useCurrencyFormatter(currencyCode = 'USD') {
  const formatter = useMemo(
    () =>
      new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currencyCode,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
    [currencyCode],
  );

  return useCallback(
    (value: string | number) => {
      const num = typeof value === 'string' ? parseFloat(value) : value;
      return isNaN(num) ? '$0.00' : formatter.format(num);
    },
    [formatter],
  );
}

/**
 * Hook for paginated data fetching with search and filters.
 */
export function usePaginatedFetch<T>(
  fetchFn: (params: Record<string, string>) => Promise<any>,
  baseParams: Record<string, string>,
) {
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { ...baseParams, page: String(page) };
      if (search) params.search = search;
      const res = await fetchFn(params);
      setItems(res.data?.results || []);
      setTotal(res.data?.count || 0);
    } finally {
      setLoading(false);
    }
  }, [fetchFn, baseParams, page, search]);

  useEffect(() => { load(); }, [load]);

  return { items, total, page, setPage, search, setSearch, loading, reload: load };
}
