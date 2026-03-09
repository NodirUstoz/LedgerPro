/**
 * Tax slice -- tax rates, filings, and calculator state management.
 */

import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import {
  taxFilingsApi,
  taxRatesApi,
  type TaxCalculationResult,
  type TaxFiling,
  type TaxRate,
} from '../api/tax';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface TaxState {
  taxRates: TaxRate[];
  filings: TaxFiling[];
  calculationResult: TaxCalculationResult | null;
  loading: boolean;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Thunks                                                             */
/* ------------------------------------------------------------------ */
export const fetchTaxRates = createAsyncThunk(
  'tax/fetchRates',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await taxRatesApi.list(params);
      return data.results;
    } catch {
      return rejectWithValue('Failed to load tax rates.');
    }
  },
);

export const fetchTaxFilings = createAsyncThunk(
  'tax/fetchFilings',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await taxFilingsApi.list(params);
      return data.results;
    } catch {
      return rejectWithValue('Failed to load tax filings.');
    }
  },
);

export const calculateTax = createAsyncThunk(
  'tax/calculate',
  async (
    payload: { amount: string; tax_rate_id: string; is_inclusive?: boolean },
    { rejectWithValue },
  ) => {
    try {
      const { data } = await taxRatesApi.calculate(payload);
      return data;
    } catch {
      return rejectWithValue('Failed to calculate tax.');
    }
  },
);

export const calculateFiling = createAsyncThunk(
  'tax/calculateFiling',
  async (id: string, { rejectWithValue }) => {
    try {
      const { data } = await taxFilingsApi.calculate(id);
      return data;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.error || 'Failed to calculate filing.');
    }
  },
);

export const fileTaxReturn = createAsyncThunk(
  'tax/file',
  async ({ id, confirmationNumber }: { id: string; confirmationNumber?: string }, { rejectWithValue }) => {
    try {
      const { data } = await taxFilingsApi.file(id, confirmationNumber);
      return data;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.error || 'Failed to file return.');
    }
  },
);

/* ------------------------------------------------------------------ */
/*  Slice                                                              */
/* ------------------------------------------------------------------ */
const initialState: TaxState = {
  taxRates: [],
  filings: [],
  calculationResult: null,
  loading: false,
  error: null,
};

const taxSlice = createSlice({
  name: 'tax',
  initialState,
  reducers: {
    clearCalculation(state) {
      state.calculationResult = null;
    },
    clearTaxError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchTaxRates.pending, (state) => { state.loading = true; })
      .addCase(fetchTaxRates.fulfilled, (state, action) => {
        state.loading = false;
        state.taxRates = action.payload;
      })
      .addCase(fetchTaxRates.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchTaxFilings.pending, (state) => { state.loading = true; })
      .addCase(fetchTaxFilings.fulfilled, (state, action) => {
        state.loading = false;
        state.filings = action.payload;
      })
      .addCase(fetchTaxFilings.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(calculateTax.fulfilled, (state, action) => {
        state.calculationResult = action.payload;
      })
      .addCase(calculateFiling.fulfilled, (state, action) => {
        const idx = state.filings.findIndex((f) => f.id === action.payload.id);
        if (idx !== -1) state.filings[idx] = action.payload;
      })
      .addCase(fileTaxReturn.fulfilled, (state, action) => {
        const idx = state.filings.findIndex((f) => f.id === action.payload.id);
        if (idx !== -1) state.filings[idx] = action.payload;
      });
  },
});

export const { clearCalculation, clearTaxError } = taxSlice.actions;
export default taxSlice.reducer;
