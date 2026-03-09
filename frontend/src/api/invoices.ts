/**
 * API module for invoicing -- customers, invoices, payments, credit notes.
 */

import client from './client';
import type { PaginatedResponse } from './ledger';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
export interface Customer {
  id: string;
  company: string;
  name: string;
  email: string;
  phone: string;
  tax_id: string;
  billing_address: string;
  shipping_address: string;
  payment_terms: number;
  credit_limit: string;
  currency: string;
  outstanding_balance: string;
  is_active: boolean;
  created_at: string;
}

export interface InvoiceLine {
  id?: string;
  description: string;
  quantity: string;
  unit_price: string;
  discount_percent: string;
  tax_rate: string | null;
  tax_amount?: string;
  line_total?: string;
  account: string | null;
}

export interface Invoice {
  id: string;
  company: string;
  customer: string;
  customer_name: string;
  invoice_number: string;
  status: 'draft' | 'sent' | 'partially_paid' | 'paid' | 'overdue' | 'voided';
  issue_date: string;
  due_date: string;
  currency: string;
  subtotal: string;
  tax_amount: string;
  discount_amount: string;
  total_amount: string;
  amount_paid: string;
  balance_due: string;
  notes: string;
  terms: string;
  lines: InvoiceLine[];
  created_at: string;
}

export interface Payment {
  id: string;
  company: string;
  invoice: string;
  invoice_number: string;
  payment_number: string;
  date: string;
  amount: string;
  currency: string;
  method: string;
  reference: string;
  created_at: string;
}

export interface CreditNote {
  id: string;
  company: string;
  invoice: string;
  invoice_number: string;
  credit_note_number: string;
  status: string;
  date: string;
  amount: string;
  reason: string;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/*  Customers                                                          */
/* ------------------------------------------------------------------ */
export const customersApi = {
  list: (params?: Record<string, string>) =>
    client.get<PaginatedResponse<Customer>>('/invoicing/customers/', { params }),
  get: (id: string) => client.get<Customer>(`/invoicing/customers/${id}/`),
  create: (data: Partial<Customer>) =>
    client.post<Customer>('/invoicing/customers/', data),
  update: (id: string, data: Partial<Customer>) =>
    client.patch<Customer>(`/invoicing/customers/${id}/`, data),
  delete: (id: string) => client.delete(`/invoicing/customers/${id}/`),
};

/* ------------------------------------------------------------------ */
/*  Invoices                                                           */
/* ------------------------------------------------------------------ */
export const invoicesApi = {
  list: (params?: Record<string, string>) =>
    client.get<PaginatedResponse<Invoice>>('/invoicing/invoices/', { params }),
  get: (id: string) => client.get<Invoice>(`/invoicing/invoices/${id}/`),
  create: (data: {
    company: string;
    customer: string;
    issue_date: string;
    due_date: string;
    lines: InvoiceLine[];
    notes?: string;
    terms?: string;
    discount_amount?: string;
    accounts_receivable?: string;
    revenue_account?: string;
  }) => client.post<Invoice>('/invoicing/invoices/', data),
  update: (id: string, data: Partial<Invoice>) =>
    client.patch<Invoice>(`/invoicing/invoices/${id}/`, data),
  delete: (id: string) => client.delete(`/invoicing/invoices/${id}/`),
  send: (id: string) =>
    client.post<Invoice>(`/invoicing/invoices/${id}/send_invoice/`),
  void: (id: string) =>
    client.post(`/invoicing/invoices/${id}/void_invoice/`),
  summary: (companyId: string) =>
    client.get('/invoicing/invoices/summary/', { params: { company: companyId } }),
};

/* ------------------------------------------------------------------ */
/*  Payments                                                           */
/* ------------------------------------------------------------------ */
export const paymentsApi = {
  list: (params?: Record<string, string>) =>
    client.get<PaginatedResponse<Payment>>('/invoicing/payments/', { params }),
  create: (data: Partial<Payment>) =>
    client.post<Payment>('/invoicing/payments/', data),
};

/* ------------------------------------------------------------------ */
/*  Credit Notes                                                       */
/* ------------------------------------------------------------------ */
export const creditNotesApi = {
  list: (params?: Record<string, string>) =>
    client.get<PaginatedResponse<CreditNote>>('/invoicing/credit-notes/', { params }),
  create: (data: Partial<CreditNote>) =>
    client.post<CreditNote>('/invoicing/credit-notes/', data),
  apply: (id: string) =>
    client.post(`/invoicing/credit-notes/${id}/apply/`),
};
