/**
 * Auth slice -- handles login, registration, profile, and token state.
 */

import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import client from '../api/client';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */
interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: string;
  timezone: string;
  last_active_company: string | null;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
}

/* ------------------------------------------------------------------ */
/*  Thunks                                                             */
/* ------------------------------------------------------------------ */
export const login = createAsyncThunk(
  'auth/login',
  async (credentials: { email: string; password: string }, { rejectWithValue }) => {
    try {
      const { data } = await client.post('/auth/login/', credentials);
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      return data.user as User;
    } catch (err: any) {
      return rejectWithValue(
        err.response?.data?.details?.detail || 'Login failed.',
      );
    }
  },
);

export const register = createAsyncThunk(
  'auth/register',
  async (
    payload: {
      email: string;
      password: string;
      password_confirm: string;
      first_name: string;
      last_name: string;
    },
    { rejectWithValue },
  ) => {
    try {
      const { data } = await client.post('/auth/register/', payload);
      return data.user as User;
    } catch (err: any) {
      return rejectWithValue(
        err.response?.data?.details || 'Registration failed.',
      );
    }
  },
);

export const fetchProfile = createAsyncThunk(
  'auth/fetchProfile',
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await client.get('/auth/profile/');
      return data as User;
    } catch (err: any) {
      return rejectWithValue('Failed to load profile.');
    }
  },
);

/* ------------------------------------------------------------------ */
/*  Slice                                                              */
/* ------------------------------------------------------------------ */
const initialState: AuthState = {
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  loading: false,
  error: null,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout(state) {
      state.user = null;
      state.isAuthenticated = false;
      state.error = null;
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    },
    clearError(state) {
      state.error = null;
    },
    setActiveCompany(state, action: PayloadAction<string>) {
      if (state.user) {
        state.user.last_active_company = action.payload;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload;
        state.isAuthenticated = true;
      })
      .addCase(login.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(register.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(register.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload;
      })
      .addCase(register.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(fetchProfile.fulfilled, (state, action) => {
        state.user = action.payload;
        state.isAuthenticated = true;
      })
      .addCase(fetchProfile.rejected, (state) => {
        state.isAuthenticated = false;
      });
  },
});

export const { logout, clearError, setActiveCompany } = authSlice.actions;
export default authSlice.reducer;
