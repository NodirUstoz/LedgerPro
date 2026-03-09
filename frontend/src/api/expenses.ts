/**
 * API module for expenses, vendors, and expense categories.
 */

import client from './client';
import type { PaginatedResponse } from './ledger';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
export interface ExpenseCategory {
  id: string;
  company: string;
  name: string;
  description: string;
  parent: string | null;
  default_account: string | null;
  budget_amount: string;
  is_active: boolean;
  spent_this_month: string;
}

export interface Vendor {
  id: string;
  company: string;
  name: string;
  email: string;
  phone: string;
  tax_id: string;
  payment_terms: number;
  currency: string;
  is_active: boolean;
}

export interface Expense {
  id: string;
  company: string;
  expense_number: string;
  vendor: string | null;
  vendor_name: string | null;
  category: string | null;
  category_name: string | null;
  date: string;
  due_date: string | null;
  description: string;
  amount: string;
  tax_amount: string;
  total_amount: string;
  currency: string;
  status: 'draft' | 'pending' | 'approved' | 'paid' | 'rejected' | 'voided';
  payment_method: string;
  reference: string;
  notes: string;
  is_billable: boolean;
  expense_account: string | null;
  payment_account: string | null;
  created_by_name: string;
  created_at: string;
}

export interface ExpenseSummary {
  total_expenses: string;
  by_category: Array<{ category__name: string; total: string }>;
  count: number;
}

/* ------------------------------------------------------------------ */
/*  Categories                                                         */
/* ------------------------------------------------------------------ */
export const expenseCategoriesApi = {
  list: (params?: Record<string, string>) =>
    client.get<PaginatedResponse<ExpenseCategory>>('/expenses/categories/', { params }),
  create: (data: Partial<ExpenseCategory>) =>
    client.post<ExpenseCategory>('/expenses/categories/', data),
  update: (id: string, data: Partial<ExpenseCategory>) =>
    client.patch<ExpenseCategory>(`/expenses/categories/${id}/`, data),
  delete: (id: string) => client.delete(`/expenses/categories/${id}/`),
};

/* ------------------------------------------------------------------ */
/*  Vendors                                                            */
/* ------------------------------------------------------------------ */
export const vendorsApi = {
  list: (params?: Record<string, string>) =>
    client.get<PaginatedResponse<Vendor>>('/expenses/vendors/', { params }),
  get: (id: string) => client.get<Vendor>(`/expenses/vendors/${id}/`),
  create: (data: Partial<Vendor>) =>
    client.post<Vendor>('/expenses/vendors/', data),
  update: (id: string, data: Partial<Vendor>) =>
    client.patch<Vendor>(`/expenses/vendors/${id}/`, data),
  delete: (id: string) => client.delete(`/expenses/vendors/${id}/`),
};

/* ------------------------------------------------------------------ */
/*  Expenses                                                           */
/* ------------------------------------------------------------------ */
export const expensesApi = {
  list: (params?: Record<string, string>) =>
    client.get<PaginatedResponse<Expense>>('/expenses/expenses/', { params }),
  get: (id: string) => client.get<Expense>(`/expenses/expenses/${id}/`),
  create: (data: Partial<Expense>) =>
    client.post<Expense>('/expenses/expenses/', data),
  update: (id: string, data: Partial<Expense>) =>
    client.patch<Expense>(`/expenses/expenses/${id}/`, data),
  delete: (id: string) => client.delete(`/expenses/expenses/${id}/`),
  approve: (id: string) =>
    client.post<Expense>(`/expenses/expenses/${id}/approve/`),
  reject: (id: string) =>
    client.post(`/expenses/expenses/${id}/reject/`),
  recordPayment: (id: string) =>
    client.post<Expense>(`/expenses/expenses/${id}/record_payment/`),
  uploadReceipt: (id: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return client.post(`/expenses/expenses/${id}/upload_receipt/`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  summary: (params: Record<string, string>) =>
    client.get<ExpenseSummary>('/expenses/expenses/summary/', { params }),
};
