/**
 * Invoice slice -- invoices, customers, payments state management.
 */

import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import {
  customersApi,
  invoicesApi,
  paymentsApi,
  type Customer,
  type Invoice,
  type Payment,
} from '../api/invoices';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface InvoiceState {
  customers: Customer[];
  invoices: Invoice[];
  payments: Payment[];
  loading: boolean;
  totalInvoices: number;
  summary: {
    total_invoices: number;
    total_outstanding: string;
    total_revenue: string;
    overdue: number;
  } | null;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Thunks                                                             */
/* ------------------------------------------------------------------ */
export const fetchCustomers = createAsyncThunk(
  'invoices/fetchCustomers',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await customersApi.list(params);
      return data.results;
    } catch {
      return rejectWithValue('Failed to load customers.');
    }
  },
);

export const fetchInvoices = createAsyncThunk(
  'invoices/fetchInvoices',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await invoicesApi.list(params);
      return { results: data.results, count: data.count };
    } catch {
      return rejectWithValue('Failed to load invoices.');
    }
  },
);

export const sendInvoice = createAsyncThunk(
  'invoices/sendInvoice',
  async (id: string, { rejectWithValue }) => {
    try {
      const { data } = await invoicesApi.send(id);
      return data;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.error || 'Failed to send invoice.');
    }
  },
);

export const fetchInvoiceSummary = createAsyncThunk(
  'invoices/fetchSummary',
  async (companyId: string, { rejectWithValue }) => {
    try {
      const { data } = await invoicesApi.summary(companyId);
      return data;
    } catch {
      return rejectWithValue('Failed to load invoice summary.');
    }
  },
);

export const fetchPayments = createAsyncThunk(
  'invoices/fetchPayments',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await paymentsApi.list(params);
      return data.results;
    } catch {
      return rejectWithValue('Failed to load payments.');
    }
  },
);

/* ------------------------------------------------------------------ */
/*  Slice                                                              */
/* ------------------------------------------------------------------ */
const initialState: InvoiceState = {
  customers: [],
  invoices: [],
  payments: [],
  loading: false,
  totalInvoices: 0,
  summary: null,
  error: null,
};

const invoiceSlice = createSlice({
  name: 'invoices',
  initialState,
  reducers: {
    clearInvoiceError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCustomers.fulfilled, (state, action) => {
        state.customers = action.payload;
      })
      .addCase(fetchInvoices.pending, (state) => { state.loading = true; })
      .addCase(fetchInvoices.fulfilled, (state, action) => {
        state.loading = false;
        state.invoices = action.payload.results;
        state.totalInvoices = action.payload.count;
      })
      .addCase(fetchInvoices.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(sendInvoice.fulfilled, (state, action) => {
        const idx = state.invoices.findIndex((i) => i.id === action.payload.id);
        if (idx !== -1) state.invoices[idx] = action.payload;
      })
      .addCase(fetchInvoiceSummary.fulfilled, (state, action) => {
        state.summary = action.payload;
      })
      .addCase(fetchPayments.fulfilled, (state, action) => {
        state.payments = action.payload;
      });
  },
});

export const { clearInvoiceError } = invoiceSlice.actions;
export default invoiceSlice.reducer;
