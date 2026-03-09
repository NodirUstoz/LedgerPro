/**
 * API module for tax rates, filings, and exemptions.
 */

import client from './client';
import type { PaginatedResponse } from './ledger';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
export interface TaxRate {
  id: string;
  company: string;
  name: string;
  code: string;
  tax_type: string;
  rate: string;
  is_compound: boolean;
  is_inclusive: boolean;
  applies_to: 'sales' | 'purchases' | 'both';
  tax_account: string | null;
  is_active: boolean;
  effective_from: string | null;
  effective_to: string | null;
}

export interface TaxFiling {
  id: string;
  company: string;
  name: string;
  tax_type: string;
  frequency: string;
  period_start: string;
  period_end: string;
  filing_deadline: string;
  total_taxable_sales: string;
  total_tax_collected: string;
  total_taxable_purchases: string;
  total_input_tax: string;
  net_tax_liability: string;
  adjustments: string;
  total_due: string;
  status: 'draft' | 'calculated' | 'filed' | 'amended';
  filed_date: string | null;
  confirmation_number: string;
}

export interface TaxCalculationResult {
  tax_rate_name: string;
  tax_rate_percent: string;
  net_amount: string;
  tax_amount: string;
  gross_amount: string;
}

/* ------------------------------------------------------------------ */
/*  Tax Rates                                                          */
/* ------------------------------------------------------------------ */
export const taxRatesApi = {
  list: (params?: Record<string, string>) =>
    client.get<PaginatedResponse<TaxRate>>('/tax/rates/', { params }),
  get: (id: string) => client.get<TaxRate>(`/tax/rates/${id}/`),
  create: (data: Partial<TaxRate>) =>
    client.post<TaxRate>('/tax/rates/', data),
  update: (id: string, data: Partial<TaxRate>) =>
    client.patch<TaxRate>(`/tax/rates/${id}/`, data),
  delete: (id: string) => client.delete(`/tax/rates/${id}/`),
  calculate: (data: { amount: string; tax_rate_id: string; is_inclusive?: boolean }) =>
    client.post<TaxCalculationResult>('/tax/rates/calculate/', data),
};

/* ------------------------------------------------------------------ */
/*  Tax Filings                                                        */
/* ------------------------------------------------------------------ */
export const taxFilingsApi = {
  list: (params?: Record<string, string>) =>
    client.get<PaginatedResponse<TaxFiling>>('/tax/filings/', { params }),
  get: (id: string) => client.get<TaxFiling>(`/tax/filings/${id}/`),
  create: (data: Partial<TaxFiling>) =>
    client.post<TaxFiling>('/tax/filings/', data),
  update: (id: string, data: Partial<TaxFiling>) =>
    client.patch<TaxFiling>(`/tax/filings/${id}/`, data),
  calculate: (id: string) =>
    client.post<TaxFiling>(`/tax/filings/${id}/calculate/`),
  file: (id: string, confirmationNumber?: string) =>
    client.post<TaxFiling>(`/tax/filings/${id}/file/`, {
      confirmation_number: confirmationNumber,
    }),
  recordPayment: (id: string, paymentAccountId: string) =>
    client.post<TaxFiling>(`/tax/filings/${id}/record_payment/`, {
      payment_account_id: paymentAccountId,
    }),
};
