/**
 * LedgerPage -- chart of accounts management and account ledger views.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import { fetchAccounts, createAccount } from '../store/ledgerSlice';
import { useCurrencyFormatter } from '../hooks/useAccounting';
import { accountTypeLabel, formatCurrency, formatDate } from '../utils/formatters';
import { accountsApi, type Account } from '../api/ledger';

const ACCOUNT_TYPES = ['asset', 'liability', 'equity', 'revenue', 'expense'] as const;

const LedgerPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const companyId = useAppSelector((s) => s.auth.user?.last_active_company) || '';
  const { accounts, accountsLoading } = useAppSelector((s) => s.ledger);
  const fmt = useCurrencyFormatter();

  const [typeFilter, setTypeFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    code: '', name: '', description: '', account_type: 'asset',
    sub_type: '', normal_balance: 'debit', parent: '',
    opening_balance: '0.00',
  });

  useEffect(() => {
    if (companyId) {
      const params: Record<string, string> = { company: companyId };
      if (typeFilter) params.type = typeFilter;
      if (searchTerm) params.search = searchTerm;
      dispatch(fetchAccounts(params));
    }
  }, [dispatch, companyId, typeFilter, searchTerm]);

  const handleCreateAccount = useCallback(async () => {
    if (!formData.code || !formData.name) return;
    await dispatch(createAccount({
      ...formData,
      company: companyId,
      parent: formData.parent || null,
    } as Partial<Account>));
    setShowForm(false);
    setFormData({
      code: '', name: '', description: '', account_type: 'asset',
      sub_type: '', normal_balance: 'debit', parent: '',
      opening_balance: '0.00',
    });
  }, [dispatch, companyId, formData]);

  const grouped = React.useMemo(() => {
    const g: Record<string, typeof accounts> = {};
    for (const acct of accounts) {
      const t = acct.account_type;
      if (!g[t]) g[t] = [];
      g[t].push(acct);
    }
    return g;
  }, [accounts]);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Chart of Accounts</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {showForm ? 'Cancel' : 'New Account'}
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <input
          type="text"
          placeholder="Search accounts..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">All Types</option>
          {ACCOUNT_TYPES.map((t) => (
            <option key={t} value={t}>{accountTypeLabel(t)}</option>
          ))}
        </select>
      </div>

      {/* Create Account Form */}
      {showForm && (
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h3 className="text-lg font-semibold">Create New Account</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input
              placeholder="Account Code (e.g. 1000)"
              value={formData.code}
              onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg"
            />
            <input
              placeholder="Account Name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg"
            />
            <select
              value={formData.account_type}
              onChange={(e) => setFormData({ ...formData, account_type: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg"
            >
              {ACCOUNT_TYPES.map((t) => (
                <option key={t} value={t}>{accountTypeLabel(t)}</option>
              ))}
            </select>
            <input
              placeholder="Opening Balance"
              type="number"
              step="0.01"
              value={formData.opening_balance}
              onChange={(e) => setFormData({ ...formData, opening_balance: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg"
            />
            <textarea
              placeholder="Description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg md:col-span-2"
              rows={1}
            />
          </div>
          <button
            onClick={handleCreateAccount}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            Save Account
          </button>
        </div>
      )}

      {/* Accounts Table Grouped by Type */}
      {accountsLoading ? (
        <div className="text-center py-12 text-gray-500">Loading accounts...</div>
      ) : (
        Object.entries(grouped).map(([type, accts]) => (
          <div key={type} className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-800">{accountTypeLabel(type)}</h2>
            </div>
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sub-Type</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Balance</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {accts.map((acct) => (
                  <tr key={acct.id} className="hover:bg-gray-50 cursor-pointer">
                    <td className="px-6 py-3 text-sm font-mono text-blue-600">{acct.code}</td>
                    <td className="px-6 py-3 text-sm text-gray-900">{acct.name}</td>
                    <td className="px-6 py-3 text-sm text-gray-500">{acct.sub_type || '--'}</td>
                    <td className="px-6 py-3 text-sm text-right font-medium">{fmt(acct.current_balance)}</td>
                    <td className="px-6 py-3 text-center">
                      <span className={`inline-block w-2 h-2 rounded-full ${acct.is_active ? 'bg-green-500' : 'bg-gray-400'}`} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  );
};

export default LedgerPage;
