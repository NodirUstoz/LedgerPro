/**
 * Redux store configuration for LedgerPro.
 */

import { configureStore } from '@reduxjs/toolkit';
import { TypedUseSelectorHook, useDispatch, useSelector } from 'react-redux';

import authReducer from './authSlice';
import ledgerReducer from './ledgerSlice';
import invoiceReducer from './invoiceSlice';
import expenseReducer from './expenseSlice';
import reportReducer from './reportSlice';
import taxReducer from './taxSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    ledger: ledgerReducer,
    invoices: invoiceReducer,
    expenses: expenseReducer,
    reports: reportReducer,
    tax: taxReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({ serializableCheck: false }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
