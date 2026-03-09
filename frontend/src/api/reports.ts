/**
 * API module for financial reports and statements.
 */

import client from './client';
import type { PaginatedResponse } from './ledger';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
export interface IncomeStatementItem {
  account_code: string;
  account_name: string;
  sub_type: string;
  amount: string;
}

export interface IncomeStatement {
  company: string;
  period_start: string;
  period_end: string;
  revenue: { items: IncomeStatementItem[]; total: string };
  expenses: { items: IncomeStatementItem[]; total: string };
  net_income: string;
  prior_period?: {
    period_start: string;
    period_end: string;
    total_revenue: string;
    total_expenses: string;
    net_income: string;
  };
}

export interface BalanceSheetSection {
  items: Array<{
    account_code: string;
    account_name: string;
    sub_type: string;
    balance: string;
  }>;
  total: string;
}

export interface BalanceSheet {
  company: string;
  as_of_date: string;
  assets: BalanceSheetSection;
  liabilities: BalanceSheetSection;
  equity: BalanceSheetSection;
  total_liabilities_and_equity: string;
  is_balanced: boolean;
}

export interface CashFlowStatement {
  company: string;
  period_start: string;
  period_end: string;
  operating_activities: {
    net_income: string;
    ar_change: string;
    ap_change: string;
    total: string;
  };
  investing_activities: { total: string };
  financing_activities: { total: string };
  net_change_in_cash: string;
  opening_cash_balance: string;
  closing_cash_balance: string;
}

export interface SavedReport {
  id: string;
  company: string;
  name: string;
  report_type: string;
  report_type_display: string;
  period_start: string | null;
  period_end: string | null;
  file_format: string;
  is_favorite: boolean;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/*  Financial Statements                                               */
/* ------------------------------------------------------------------ */
export const statementsApi = {
  incomeStatement: (params: {
    company: string;
    start_date: string;
    end_date: string;
    compare_prior_period?: string;
  }) => client.get<IncomeStatement>('/reports/statements/income_statement/', { params }),

  balanceSheet: (params: { company: string; as_of_date?: string }) =>
    client.get<BalanceSheet>('/reports/statements/balance_sheet/', { params }),

  cashFlow: (params: {
    company: string;
    start_date: string;
    end_date: string;
  }) => client.get<CashFlowStatement>('/reports/statements/cash_flow/', { params }),
};

/* ------------------------------------------------------------------ */
/*  Saved Reports                                                      */
/* ------------------------------------------------------------------ */
export const savedReportsApi = {
  list: (params?: Record<string, string>) =>
    client.get<PaginatedResponse<SavedReport>>('/reports/saved/', { params }),
  get: (id: string) => client.get<SavedReport>(`/reports/saved/${id}/`),
  create: (data: Partial<SavedReport>) =>
    client.post<SavedReport>('/reports/saved/', data),
  delete: (id: string) => client.delete(`/reports/saved/${id}/`),
  toggleFavorite: (id: string) =>
    client.post(`/reports/saved/${id}/toggle_favorite/`),
};
