/**
 * Expense slice -- expenses, vendors, and categories state management.
 */

import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import {
  expenseCategoriesApi,
  expensesApi,
  vendorsApi,
  type Expense,
  type ExpenseCategory,
  type ExpenseSummary,
  type Vendor,
} from '../api/expenses';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface ExpenseState {
  expenses: Expense[];
  categories: ExpenseCategory[];
  vendors: Vendor[];
  loading: boolean;
  totalExpenses: number;
  summary: ExpenseSummary | null;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Thunks                                                             */
/* ------------------------------------------------------------------ */
export const fetchExpenses = createAsyncThunk(
  'expenses/fetchExpenses',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await expensesApi.list(params);
      return { results: data.results, count: data.count };
    } catch {
      return rejectWithValue('Failed to load expenses.');
    }
  },
);

export const fetchCategories = createAsyncThunk(
  'expenses/fetchCategories',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await expenseCategoriesApi.list(params);
      return data.results;
    } catch {
      return rejectWithValue('Failed to load expense categories.');
    }
  },
);

export const fetchVendors = createAsyncThunk(
  'expenses/fetchVendors',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await vendorsApi.list(params);
      return data.results;
    } catch {
      return rejectWithValue('Failed to load vendors.');
    }
  },
);

export const approveExpense = createAsyncThunk(
  'expenses/approveExpense',
  async (id: string, { rejectWithValue }) => {
    try {
      const { data } = await expensesApi.approve(id);
      return data;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.error || 'Failed to approve expense.');
    }
  },
);

export const recordExpensePayment = createAsyncThunk(
  'expenses/recordPayment',
  async (id: string, { rejectWithValue }) => {
    try {
      const { data } = await expensesApi.recordPayment(id);
      return data;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.error || 'Failed to record payment.');
    }
  },
);

export const fetchExpenseSummary = createAsyncThunk(
  'expenses/fetchSummary',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await expensesApi.summary(params);
      return data;
    } catch {
      return rejectWithValue('Failed to load expense summary.');
    }
  },
);

/* ------------------------------------------------------------------ */
/*  Slice                                                              */
/* ------------------------------------------------------------------ */
const initialState: ExpenseState = {
  expenses: [],
  categories: [],
  vendors: [],
  loading: false,
  totalExpenses: 0,
  summary: null,
  error: null,
};

const expenseSlice = createSlice({
  name: 'expenses',
  initialState,
  reducers: {
    clearExpenseError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchExpenses.pending, (state) => { state.loading = true; })
      .addCase(fetchExpenses.fulfilled, (state, action) => {
        state.loading = false;
        state.expenses = action.payload.results;
        state.totalExpenses = action.payload.count;
      })
      .addCase(fetchExpenses.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchCategories.fulfilled, (state, action) => {
        state.categories = action.payload;
      })
      .addCase(fetchVendors.fulfilled, (state, action) => {
        state.vendors = action.payload;
      })
      .addCase(approveExpense.fulfilled, (state, action) => {
        const idx = state.expenses.findIndex((e) => e.id === action.payload.id);
        if (idx !== -1) state.expenses[idx] = action.payload;
      })
      .addCase(recordExpensePayment.fulfilled, (state, action) => {
        const idx = state.expenses.findIndex((e) => e.id === action.payload.id);
        if (idx !== -1) state.expenses[idx] = action.payload;
      })
      .addCase(fetchExpenseSummary.fulfilled, (state, action) => {
        state.summary = action.payload;
      });
  },
});

export const { clearExpenseError } = expenseSlice.actions;
export default expenseSlice.reducer;
