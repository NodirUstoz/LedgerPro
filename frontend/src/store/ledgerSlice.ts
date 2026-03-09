/**
 * Ledger slice -- chart of accounts and journal entries state management.
 */

import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { accountsApi, journalEntriesApi, type Account, type JournalEntry } from '../api/ledger';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface LedgerState {
  accounts: Account[];
  accountsLoading: boolean;
  journalEntries: JournalEntry[];
  journalEntriesLoading: boolean;
  totalEntries: number;
  currentPage: number;
  selectedEntry: JournalEntry | null;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Thunks                                                             */
/* ------------------------------------------------------------------ */
export const fetchAccounts = createAsyncThunk(
  'ledger/fetchAccounts',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await accountsApi.list(params);
      return data.results;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.error || 'Failed to load accounts.');
    }
  },
);

export const fetchAccountTree = createAsyncThunk(
  'ledger/fetchAccountTree',
  async (companyId: string, { rejectWithValue }) => {
    try {
      const { data } = await accountsApi.tree(companyId);
      return data;
    } catch (err: any) {
      return rejectWithValue('Failed to load account tree.');
    }
  },
);

export const createAccount = createAsyncThunk(
  'ledger/createAccount',
  async (payload: Partial<Account>, { rejectWithValue }) => {
    try {
      const { data } = await accountsApi.create(payload);
      return data;
    } catch (err: any) {
      return rejectWithValue(err.response?.data || 'Failed to create account.');
    }
  },
);

export const fetchJournalEntries = createAsyncThunk(
  'ledger/fetchJournalEntries',
  async (params: Record<string, string>, { rejectWithValue }) => {
    try {
      const { data } = await journalEntriesApi.list(params);
      return { results: data.results, count: data.count, page: data.current_page };
    } catch (err: any) {
      return rejectWithValue('Failed to load journal entries.');
    }
  },
);

export const postJournalEntry = createAsyncThunk(
  'ledger/postJournalEntry',
  async (id: string, { rejectWithValue }) => {
    try {
      const { data } = await journalEntriesApi.post(id);
      return data;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.error || 'Failed to post entry.');
    }
  },
);

export const voidJournalEntry = createAsyncThunk(
  'ledger/voidJournalEntry',
  async (id: string, { rejectWithValue }) => {
    try {
      const { data } = await journalEntriesApi.void(id);
      return data;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.error || 'Failed to void entry.');
    }
  },
);

/* ------------------------------------------------------------------ */
/*  Slice                                                              */
/* ------------------------------------------------------------------ */
const initialState: LedgerState = {
  accounts: [],
  accountsLoading: false,
  journalEntries: [],
  journalEntriesLoading: false,
  totalEntries: 0,
  currentPage: 1,
  selectedEntry: null,
  error: null,
};

const ledgerSlice = createSlice({
  name: 'ledger',
  initialState,
  reducers: {
    setSelectedEntry(state, action) {
      state.selectedEntry = action.payload;
    },
    clearLedgerError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAccounts.pending, (state) => { state.accountsLoading = true; })
      .addCase(fetchAccounts.fulfilled, (state, action) => {
        state.accountsLoading = false;
        state.accounts = action.payload;
      })
      .addCase(fetchAccounts.rejected, (state, action) => {
        state.accountsLoading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchAccountTree.fulfilled, (state, action) => {
        state.accounts = action.payload;
        state.accountsLoading = false;
      })
      .addCase(createAccount.fulfilled, (state, action) => {
        state.accounts.push(action.payload);
      })
      .addCase(fetchJournalEntries.pending, (state) => {
        state.journalEntriesLoading = true;
      })
      .addCase(fetchJournalEntries.fulfilled, (state, action) => {
        state.journalEntriesLoading = false;
        state.journalEntries = action.payload.results;
        state.totalEntries = action.payload.count;
        state.currentPage = action.payload.page;
      })
      .addCase(fetchJournalEntries.rejected, (state, action) => {
        state.journalEntriesLoading = false;
        state.error = action.payload as string;
      })
      .addCase(postJournalEntry.fulfilled, (state, action) => {
        const idx = state.journalEntries.findIndex((e) => e.id === action.payload.id);
        if (idx !== -1) state.journalEntries[idx] = action.payload;
      })
      .addCase(voidJournalEntry.fulfilled, (state, action) => {
        const idx = state.journalEntries.findIndex((e) => e.id === action.payload.id);
        if (idx !== -1) state.journalEntries[idx] = action.payload;
      });
  },
});

export const { setSelectedEntry, clearLedgerError } = ledgerSlice.actions;
export default ledgerSlice.reducer;
