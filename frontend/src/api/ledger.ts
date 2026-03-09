/**
 * API module for Chart of Accounts and Journal Entry operations.
 */

import client from './client';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
export interface Account {
  id: string;
  company: string;
  code: string;
  name: string;
  description: string;
  account_type: 'asset' | 'liability' | 'equity' | 'revenue' | 'expense';
  sub_type: string;
  normal_balance: 'debit' | 'credit';
  parent: string | null;
  parent_name: string | null;
  currency: string;
  is_active: boolean;
  is_system: boolean;
  tax_rate: string | null;
  opening_balance: string;
  current_balance: string;
  full_path: string;
  children_count: number;
  created_at: string;
  updated_at: string;
}

export interface JournalLine {
  id?: string;
  account: string;
  account_code?: string;
  account_name?: string;
  description: string;
  debit_amount: string;
  credit_amount: string;
}

export interface JournalEntry {
  id: string;
  company: string;
  entry_number: string;
  date: string;
  description: string;
  reference: string;
  entry_type: string;
  status: 'draft' | 'pending' | 'posted' | 'voided';
  total_debit: string;
  total_credit: string;
  is_balanced: boolean;
  lines: JournalLine[];
  created_by_name: string;
  created_at: string;
}

export interface PaginatedResponse<T> {
  count: number;
  total_pages: number;
  current_page: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/* ------------------------------------------------------------------ */
/*  Chart of Accounts                                                  */
/* ------------------------------------------------------------------ */
export const accountsApi = {
  list(params?: Record<string, string>) {
    return client.get<PaginatedResponse<Account>>('/ledger/accounts/', { params });
  },

  tree(companyId: string) {
    return client.get<Account[]>('/ledger/accounts/tree/', {
      params: { company: companyId },
    });
  },

  get(id: string) {
    return client.get<Account>(`/ledger/accounts/${id}/`);
  },

  create(data: Partial<Account>) {
    return client.post<Account>('/ledger/accounts/', data);
  },

  update(id: string, data: Partial<Account>) {
    return client.patch<Account>(`/ledger/accounts/${id}/`, data);
  },

  delete(id: string) {
    return client.delete(`/ledger/accounts/${id}/`);
  },

  ledger(id: string, params?: Record<string, string>) {
    return client.get<PaginatedResponse<JournalLine>>(`/ledger/accounts/${id}/ledger/`, { params });
  },
};

/* ------------------------------------------------------------------ */
/*  Journal Entries                                                    */
/* ------------------------------------------------------------------ */
export const journalEntriesApi = {
  list(params?: Record<string, string>) {
    return client.get<PaginatedResponse<JournalEntry>>('/ledger/journal-entries/', { params });
  },

  get(id: string) {
    return client.get<JournalEntry>(`/ledger/journal-entries/${id}/`);
  },

  create(data: {
    company: string;
    date: string;
    description: string;
    reference?: string;
    entry_type?: string;
    lines: Omit<JournalLine, 'id' | 'account_code' | 'account_name'>[];
  }) {
    return client.post<JournalEntry>('/ledger/journal-entries/', data);
  },

  update(id: string, data: Partial<JournalEntry>) {
    return client.patch<JournalEntry>(`/ledger/journal-entries/${id}/`, data);
  },

  delete(id: string) {
    return client.delete(`/ledger/journal-entries/${id}/`);
  },

  post(id: string) {
    return client.post<JournalEntry>(`/ledger/journal-entries/${id}/post_entry/`);
  },

  void(id: string) {
    return client.post<JournalEntry>(`/ledger/journal-entries/${id}/void/`);
  },

  reverse(id: string, reversalDate?: string) {
    return client.post<JournalEntry>(`/ledger/journal-entries/${id}/reverse/`, {
      reversal_date: reversalDate,
    });
  },
};

/* ------------------------------------------------------------------ */
/*  Trial Balance                                                      */
/* ------------------------------------------------------------------ */
export const trialBalanceApi = {
  get(companyId: string, asOfDate?: string) {
    return client.get('/ledger/trial-balance/', {
      params: { company: companyId, as_of_date: asOfDate },
    });
  },
};
