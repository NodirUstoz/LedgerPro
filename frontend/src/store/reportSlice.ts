/**
 * Report slice -- financial statements and saved reports state management.
 */

import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import {
  savedReportsApi,
  statementsApi,
  type BalanceSheet,
  type CashFlowStatement,
  type IncomeStatement,
  type SavedReport,
} from '../api/reports';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface ReportState {
  incomeStatement: IncomeStatement | null;
  balanceSheet: BalanceSheet | null;
  cashFlow: CashFlowStatement | null;
  savedReports: SavedReport[];
  loading: boolean;
  statementLoading: boolean;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Thunks                                                             */
/* ------------------------------------------------------------------ */
export const fetchIncomeStatement = createAsyncThunk(
  'reports/fetchIncomeStatement',
  async (
    params: { company: string; start_date: string; end_date: string; compare_prior_period?: string },
    { rejectWithValue },
  ) => {
    try {
      const { data } = await statementsApi.incomeStatement(params);
      return data;
    } catch {
      return rejectWithValue('Failed to generate income statement.');
    }
  },
);

export const fetchBalanceSheet = createAsyncThunk(
  'reports/fetchBalanceSheet',
  async (params: { company: string; as_of_date?: string }, { rejectWithValue }) => {
    try {
      const { data } = await statementsApi.balanceSheet(params);
      return data;
    } catch {
      return rejectWithValue('Failed to generate balance sheet.');
    }
  },
);

export const fetchCashFlow = createAsyncThunk(
  'reports/fetchCashFlow',
  async (
    params: { company: string; start_date: string; end_date: string },
    { rejectWithValue },
  ) => {
    try {
      const { data } = await statementsApi.cashFlow(params);
      return data;
    } catch {
      return rejectWithValue('Failed to generate cash flow statement.');
    }
  },
);

export const fetchSavedReports = createAsyncThunk(
  'reports/fetchSaved',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await savedReportsApi.list(params);
      return data.results;
    } catch {
      return rejectWithValue('Failed to load saved reports.');
    }
  },
);

/* ------------------------------------------------------------------ */
/*  Slice                                                              */
/* ------------------------------------------------------------------ */
const initialState: ReportState = {
  incomeStatement: null,
  balanceSheet: null,
  cashFlow: null,
  savedReports: [],
  loading: false,
  statementLoading: false,
  error: null,
};

const reportSlice = createSlice({
  name: 'reports',
  initialState,
  reducers: {
    clearReport(state) {
      state.incomeStatement = null;
      state.balanceSheet = null;
      state.cashFlow = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchIncomeStatement.pending, (state) => { state.statementLoading = true; })
      .addCase(fetchIncomeStatement.fulfilled, (state, action) => {
        state.statementLoading = false;
        state.incomeStatement = action.payload;
      })
      .addCase(fetchIncomeStatement.rejected, (state, action) => {
        state.statementLoading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchBalanceSheet.pending, (state) => { state.statementLoading = true; })
      .addCase(fetchBalanceSheet.fulfilled, (state, action) => {
        state.statementLoading = false;
        state.balanceSheet = action.payload;
      })
      .addCase(fetchBalanceSheet.rejected, (state, action) => {
        state.statementLoading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchCashFlow.pending, (state) => { state.statementLoading = true; })
      .addCase(fetchCashFlow.fulfilled, (state, action) => {
        state.statementLoading = false;
        state.cashFlow = action.payload;
      })
      .addCase(fetchCashFlow.rejected, (state, action) => {
        state.statementLoading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchSavedReports.pending, (state) => { state.loading = true; })
      .addCase(fetchSavedReports.fulfilled, (state, action) => {
        state.loading = false;
        state.savedReports = action.payload;
      })
      .addCase(fetchSavedReports.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { clearReport } = reportSlice.actions;
export default reportSlice.reducer;
