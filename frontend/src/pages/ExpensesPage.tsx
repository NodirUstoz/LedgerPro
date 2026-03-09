/**
 * ExpensesPage -- expense tracking, approval workflow, receipt uploads.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import {
  fetchExpenses,
  fetchCategories,
  fetchVendors,
  approveExpense,
  recordExpensePayment,
  fetchExpenseSummary,
} from '../store/expenseSlice';
import { expensesApi } from '../api/expenses';
import { formatCurrency, formatDate, statusColor } from '../utils/formatters';

const ExpensesPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const companyId = useAppSelector((s) => s.auth.user?.last_active_company) || '';
  const { expenses, categories, vendors, loading, totalExpenses, summary } =
    useAppSelector((s) => s.expenses);

  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [formErrors, setFormErrors] = useState<string[]>([]);

  const [form, setForm] = useState({
    vendor: '',
    category: '',
    date: new Date().toISOString().split('T')[0],
    description: '',
    amount: '',
    tax_amount: '0.00',
    payment_method: '',
    reference: '',
    notes: '',
    is_billable: false,
  });

  const loadData = useCallback(() => {
    if (!companyId) return;
    const params: Record<string, string> = { company: companyId };
    if (statusFilter) params.status = statusFilter;
    if (categoryFilter) params.category = categoryFilter;
    dispatch(fetchExpenses(params));
    dispatch(fetchCategories({ company: companyId }));
    dispatch(fetchVendors({ company: companyId }));

    const today = new Date().toISOString().split('T')[0];
    const yearStart = `${new Date().getFullYear()}-01-01`;
    dispatch(fetchExpenseSummary({ company: companyId, start_date: yearStart, end_date: today }));
  }, [dispatch, companyId, statusFilter, categoryFilter]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreate = async () => {
    const errors: string[] = [];
    if (!form.description.trim()) errors.push('Description is required.');
    if (!form.amount || parseFloat(form.amount) <= 0) errors.push('Amount must be positive.');
    if (!form.date) errors.push('Date is required.');

    if (errors.length > 0) { setFormErrors(errors); return; }

    try {
      await expensesApi.create({
        company: companyId,
        vendor: form.vendor || null,
        category: form.category || null,
        date: form.date,
        description: form.description,
        amount: form.amount,
        tax_amount: form.tax_amount,
        payment_method: form.payment_method,
        reference: form.reference,
        notes: form.notes,
        is_billable: form.is_billable,
      } as any);
      setShowCreate(false);
      setFormErrors([]);
      loadData();
    } catch (err: any) {
      setFormErrors([err.response?.data?.error || 'Failed to create expense.']);
    }
  };

  const handleUploadReceipt = async (expenseId: string) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*,application/pdf';
    input.onchange = async (e: any) => {
      const file = e.target.files?.[0];
      if (file) {
        await expensesApi.uploadReceipt(expenseId, file);
        loadData();
      }
    };
    input.click();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Expenses</h1>
        <button onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          {showCreate ? 'Cancel' : 'New Expense'}
        </button>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-500">Total Expenses (YTD)</p>
            <p className="text-2xl font-bold">{formatCurrency(summary.total_expenses)}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-500">Transactions</p>
            <p className="text-2xl font-bold">{summary.count}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <p className="text-sm text-gray-500">Top Category</p>
            <p className="text-2xl font-bold">
              {summary.by_category[0]?.category__name || 'N/A'}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4">
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border rounded-lg">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="paid">Paid</option>
          <option value="rejected">Rejected</option>
        </select>
        <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-4 py-2 border rounded-lg">
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* Create Expense Form */}
      {showCreate && (
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h3 className="text-lg font-semibold">Record Expense</h3>
          {formErrors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              {formErrors.map((e, i) => <p key={i} className="text-sm text-red-700">{e}</p>)}
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <select value={form.vendor}
              onChange={(e) => setForm({ ...form, vendor: e.target.value })}
              className="px-3 py-2 border rounded-lg">
              <option value="">Select Vendor</option>
              {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
            <select value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="px-3 py-2 border rounded-lg">
              <option value="">Select Category</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <input type="date" value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              className="px-3 py-2 border rounded-lg" />
            <input placeholder="Description" value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="px-3 py-2 border rounded-lg md:col-span-2" />
            <input type="number" step="0.01" placeholder="Amount" value={form.amount}
              onChange={(e) => setForm({ ...form, amount: e.target.value })}
              className="px-3 py-2 border rounded-lg" />
          </div>
          <button onClick={handleCreate}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
            Save Expense
          </button>
        </div>
      )}

      {/* Expenses Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Expense #</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Vendor</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {expenses.map((exp) => (
              <tr key={exp.id} className="hover:bg-gray-50">
                <td className="px-6 py-3 text-sm font-medium text-blue-600">{exp.expense_number}</td>
                <td className="px-6 py-3 text-sm">{exp.vendor_name || '--'}</td>
                <td className="px-6 py-3 text-sm">{exp.category_name || '--'}</td>
                <td className="px-6 py-3 text-sm">{formatDate(exp.date)}</td>
                <td className="px-6 py-3 text-sm text-right">{formatCurrency(exp.total_amount)}</td>
                <td className="px-6 py-3 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(exp.status)}`}>{exp.status}</span>
                </td>
                <td className="px-6 py-3 text-center space-x-2">
                  {(exp.status === 'draft' || exp.status === 'pending') && (
                    <button onClick={() => dispatch(approveExpense(exp.id))}
                      className="text-xs text-green-600 hover:text-green-800">Approve</button>
                  )}
                  {exp.status === 'approved' && (
                    <button onClick={() => dispatch(recordExpensePayment(exp.id))}
                      className="text-xs text-blue-600 hover:text-blue-800">Pay</button>
                  )}
                  <button onClick={() => handleUploadReceipt(exp.id)}
                    className="text-xs text-gray-600 hover:text-gray-800">Receipt</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <p className="text-center py-6 text-gray-500">Loading...</p>}
      </div>
    </div>
  );
};

export default ExpensesPage;
