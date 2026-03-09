/**
 * JournalPage -- journal entry listing, creation, posting, voiding.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import {
  fetchJournalEntries,
  postJournalEntry,
  voidJournalEntry,
  setSelectedEntry,
} from '../store/ledgerSlice';
import { journalEntriesApi } from '../api/ledger';
import { formatCurrency, formatDate, statusColor } from '../utils/formatters';
import { validateJournalBalance, validateJournalLine } from '../utils/validation';

const JournalPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const companyId = useAppSelector((s) => s.auth.user?.last_active_company) || '';
  const { journalEntries, journalEntriesLoading, totalEntries, currentPage } =
    useAppSelector((s) => s.ledger);

  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // New entry form state
  const [entryForm, setEntryForm] = useState({
    date: new Date().toISOString().split('T')[0],
    description: '',
    reference: '',
    entry_type: 'standard',
    lines: [
      { account: '', debit_amount: '', credit_amount: '', description: '' },
      { account: '', debit_amount: '', credit_amount: '', description: '' },
    ],
  });
  const [formErrors, setFormErrors] = useState<string[]>([]);

  const loadEntries = useCallback(
    (page = 1) => {
      if (!companyId) return;
      const params: Record<string, string> = {
        company: companyId,
        page: String(page),
      };
      if (statusFilter) params.status = statusFilter;
      if (search) params.search = search;
      dispatch(fetchJournalEntries(params));
    },
    [dispatch, companyId, statusFilter, search],
  );

  useEffect(() => { loadEntries(); }, [loadEntries]);

  const addLine = () => {
    setEntryForm({
      ...entryForm,
      lines: [
        ...entryForm.lines,
        { account: '', debit_amount: '', credit_amount: '', description: '' },
      ],
    });
  };

  const removeLine = (idx: number) => {
    if (entryForm.lines.length <= 2) return;
    setEntryForm({
      ...entryForm,
      lines: entryForm.lines.filter((_, i) => i !== idx),
    });
  };

  const updateLine = (idx: number, field: string, value: string) => {
    const newLines = [...entryForm.lines];
    newLines[idx] = { ...newLines[idx], [field]: value };
    setEntryForm({ ...entryForm, lines: newLines });
  };

  const handleSubmit = async () => {
    const errors: string[] = [];
    if (!entryForm.description.trim()) errors.push('Description is required.');
    if (!entryForm.date) errors.push('Date is required.');

    entryForm.lines.forEach((line, idx) => {
      const lineErrors = validateJournalLine({
        account: line.account,
        debit_amount: line.debit_amount || '0',
        credit_amount: line.credit_amount || '0',
      });
      lineErrors.forEach((e) => errors.push(`Line ${idx + 1}: ${e}`));
    });

    const balance = validateJournalBalance(
      entryForm.lines.map((l) => ({
        debit_amount: l.debit_amount || '0',
        credit_amount: l.credit_amount || '0',
      })),
    );
    if (!balance.valid) {
      errors.push(
        `Entry is not balanced. Debits: ${balance.totalDebit.toFixed(2)}, Credits: ${balance.totalCredit.toFixed(2)}`,
      );
    }

    if (errors.length > 0) {
      setFormErrors(errors);
      return;
    }

    try {
      await journalEntriesApi.create({
        company: companyId,
        date: entryForm.date,
        description: entryForm.description,
        reference: entryForm.reference,
        entry_type: entryForm.entry_type,
        lines: entryForm.lines.map((l) => ({
          account: l.account,
          description: l.description,
          debit_amount: l.debit_amount || '0.00',
          credit_amount: l.credit_amount || '0.00',
        })),
      });
      setShowCreate(false);
      setFormErrors([]);
      loadEntries();
    } catch (err: any) {
      setFormErrors([err.response?.data?.error || 'Failed to create entry.']);
    }
  };

  const handlePost = (id: string) => dispatch(postJournalEntry(id));
  const handleVoid = (id: string) => dispatch(voidJournalEntry(id));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Journal Entries</h1>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {showCreate ? 'Cancel' : 'New Entry'}
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <input
          type="text"
          placeholder="Search by entry #, description..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg"
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="pending">Pending</option>
          <option value="posted">Posted</option>
          <option value="voided">Voided</option>
        </select>
      </div>

      {/* Create Form */}
      {showCreate && (
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h3 className="text-lg font-semibold">Create Journal Entry</h3>
          {formErrors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              {formErrors.map((e, i) => (
                <p key={i} className="text-sm text-red-700">{e}</p>
              ))}
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <input type="date" value={entryForm.date}
              onChange={(e) => setEntryForm({ ...entryForm, date: e.target.value })}
              className="px-3 py-2 border rounded-lg" />
            <input placeholder="Description" value={entryForm.description}
              onChange={(e) => setEntryForm({ ...entryForm, description: e.target.value })}
              className="px-3 py-2 border rounded-lg md:col-span-2" />
          </div>

          {/* Lines */}
          <div className="space-y-2">
            <div className="grid grid-cols-12 gap-2 text-xs font-medium text-gray-500 uppercase px-1">
              <div className="col-span-4">Account</div>
              <div className="col-span-3">Debit</div>
              <div className="col-span-3">Credit</div>
              <div className="col-span-2">Actions</div>
            </div>
            {entryForm.lines.map((line, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-2">
                <input placeholder="Account ID" value={line.account}
                  onChange={(e) => updateLine(idx, 'account', e.target.value)}
                  className="col-span-4 px-3 py-2 border rounded-lg text-sm" />
                <input placeholder="0.00" type="number" step="0.01" value={line.debit_amount}
                  onChange={(e) => updateLine(idx, 'debit_amount', e.target.value)}
                  className="col-span-3 px-3 py-2 border rounded-lg text-sm text-right" />
                <input placeholder="0.00" type="number" step="0.01" value={line.credit_amount}
                  onChange={(e) => updateLine(idx, 'credit_amount', e.target.value)}
                  className="col-span-3 px-3 py-2 border rounded-lg text-sm text-right" />
                <button onClick={() => removeLine(idx)}
                  className="col-span-2 text-red-500 hover:text-red-700 text-sm">
                  Remove
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-3">
            <button onClick={addLine} className="px-3 py-1 text-sm border rounded-lg hover:bg-gray-50">
              + Add Line
            </button>
            <button onClick={handleSubmit}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
              Save Entry
            </button>
          </div>
        </div>
      )}

      {/* Entries Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entry #</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Debit</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {journalEntries.map((entry) => (
              <tr key={entry.id} className="hover:bg-gray-50">
                <td className="px-6 py-3 text-sm font-medium text-blue-600">{entry.entry_number}</td>
                <td className="px-6 py-3 text-sm">{formatDate(entry.date)}</td>
                <td className="px-6 py-3 text-sm text-gray-700">{entry.description}</td>
                <td className="px-6 py-3 text-sm text-right">{formatCurrency(entry.total_debit)}</td>
                <td className="px-6 py-3 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(entry.status)}`}>
                    {entry.status}
                  </span>
                </td>
                <td className="px-6 py-3 text-center space-x-2">
                  {entry.status === 'draft' && (
                    <button onClick={() => handlePost(entry.id)}
                      className="text-xs text-green-600 hover:text-green-800">Post</button>
                  )}
                  {entry.status === 'posted' && (
                    <button onClick={() => handleVoid(entry.id)}
                      className="text-xs text-red-600 hover:text-red-800">Void</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {journalEntriesLoading && (
          <p className="text-center py-6 text-gray-500">Loading...</p>
        )}
      </div>

      {/* Pagination */}
      <div className="flex justify-between items-center text-sm text-gray-600">
        <span>{totalEntries} total entries</span>
        <div className="flex gap-2">
          <button
            disabled={currentPage <= 1}
            onClick={() => loadEntries(currentPage - 1)}
            className="px-3 py-1 border rounded disabled:opacity-50"
          >Previous</button>
          <span className="px-3 py-1">Page {currentPage}</span>
          <button
            onClick={() => loadEntries(currentPage + 1)}
            className="px-3 py-1 border rounded"
          >Next</button>
        </div>
      </div>
    </div>
  );
};

export default JournalPage;
