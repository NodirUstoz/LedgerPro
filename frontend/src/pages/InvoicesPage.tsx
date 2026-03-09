/**
 * InvoicesPage -- invoice listing, creation, sending, payment recording.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import { fetchInvoices, fetchCustomers, sendInvoice } from '../store/invoiceSlice';
import { invoicesApi, type InvoiceLine } from '../api/invoices';
import { formatCurrency, formatDate, statusColor } from '../utils/formatters';
import { validateInvoiceLines } from '../utils/validation';

const InvoicesPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const companyId = useAppSelector((s) => s.auth.user?.last_active_company) || '';
  const { invoices, customers, loading, totalInvoices } = useAppSelector((s) => s.invoices);

  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [formErrors, setFormErrors] = useState<string[]>([]);

  const [form, setForm] = useState({
    customer: '',
    issue_date: new Date().toISOString().split('T')[0],
    due_date: '',
    notes: '',
    terms: 'Payment due within 30 days.',
    lines: [{ description: '', quantity: '1', unit_price: '', discount_percent: '0', tax_rate: null, account: null }] as InvoiceLine[],
  });

  const loadData = useCallback(() => {
    if (!companyId) return;
    const params: Record<string, string> = { company: companyId };
    if (statusFilter) params.status = statusFilter;
    if (search) params.search = search;
    dispatch(fetchInvoices(params));
    dispatch(fetchCustomers({ company: companyId }));
  }, [dispatch, companyId, statusFilter, search]);

  useEffect(() => { loadData(); }, [loadData]);

  const addLine = () => {
    setForm({
      ...form,
      lines: [...form.lines, { description: '', quantity: '1', unit_price: '', discount_percent: '0', tax_rate: null, account: null }],
    });
  };

  const removeLine = (idx: number) => {
    if (form.lines.length <= 1) return;
    setForm({ ...form, lines: form.lines.filter((_, i) => i !== idx) });
  };

  const updateLine = (idx: number, field: string, value: string) => {
    const newLines = [...form.lines];
    newLines[idx] = { ...newLines[idx], [field]: value };
    setForm({ ...form, lines: newLines });
  };

  const handleCreate = async () => {
    const errors: string[] = [];
    if (!form.customer) errors.push('Customer is required.');
    if (!form.issue_date) errors.push('Issue date is required.');
    if (!form.due_date) errors.push('Due date is required.');

    const lineErrors = validateInvoiceLines(form.lines);
    errors.push(...lineErrors);

    if (errors.length > 0) { setFormErrors(errors); return; }

    try {
      await invoicesApi.create({
        company: companyId,
        customer: form.customer,
        issue_date: form.issue_date,
        due_date: form.due_date,
        notes: form.notes,
        terms: form.terms,
        lines: form.lines,
      });
      setShowCreate(false);
      setFormErrors([]);
      loadData();
    } catch (err: any) {
      setFormErrors([err.response?.data?.error || 'Failed to create invoice.']);
    }
  };

  const handleSend = (id: string) => dispatch(sendInvoice(id));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Invoices</h1>
        <button onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          {showCreate ? 'Cancel' : 'New Invoice'}
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <input type="text" placeholder="Search invoices..." value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-4 py-2 border rounded-lg" />
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
          className="px-4 py-2 border rounded-lg">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="sent">Sent</option>
          <option value="paid">Paid</option>
          <option value="overdue">Overdue</option>
          <option value="voided">Voided</option>
        </select>
      </div>

      {/* Create Invoice Form */}
      {showCreate && (
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h3 className="text-lg font-semibold">Create Invoice</h3>
          {formErrors.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              {formErrors.map((e, i) => <p key={i} className="text-sm text-red-700">{e}</p>)}
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <select value={form.customer}
              onChange={(e) => setForm({ ...form, customer: e.target.value })}
              className="px-3 py-2 border rounded-lg">
              <option value="">Select Customer</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
            <input type="date" value={form.issue_date}
              onChange={(e) => setForm({ ...form, issue_date: e.target.value })}
              className="px-3 py-2 border rounded-lg" />
            <input type="date" value={form.due_date}
              onChange={(e) => setForm({ ...form, due_date: e.target.value })}
              className="px-3 py-2 border rounded-lg" />
          </div>

          {/* Line Items */}
          <div className="space-y-2">
            <div className="grid grid-cols-12 gap-2 text-xs font-medium text-gray-500 uppercase">
              <div className="col-span-5">Description</div>
              <div className="col-span-2">Qty</div>
              <div className="col-span-2">Unit Price</div>
              <div className="col-span-2">Discount %</div>
              <div className="col-span-1"></div>
            </div>
            {form.lines.map((line, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-2">
                <input placeholder="Item description" value={line.description}
                  onChange={(e) => updateLine(idx, 'description', e.target.value)}
                  className="col-span-5 px-3 py-2 border rounded-lg text-sm" />
                <input type="number" step="1" value={line.quantity}
                  onChange={(e) => updateLine(idx, 'quantity', e.target.value)}
                  className="col-span-2 px-3 py-2 border rounded-lg text-sm text-right" />
                <input type="number" step="0.01" placeholder="0.00" value={line.unit_price}
                  onChange={(e) => updateLine(idx, 'unit_price', e.target.value)}
                  className="col-span-2 px-3 py-2 border rounded-lg text-sm text-right" />
                <input type="number" step="0.01" value={line.discount_percent}
                  onChange={(e) => updateLine(idx, 'discount_percent', e.target.value)}
                  className="col-span-2 px-3 py-2 border rounded-lg text-sm text-right" />
                <button onClick={() => removeLine(idx)}
                  className="col-span-1 text-red-500 hover:text-red-700 text-sm">X</button>
              </div>
            ))}
          </div>
          <div className="flex gap-3">
            <button onClick={addLine} className="px-3 py-1 text-sm border rounded-lg hover:bg-gray-50">+ Add Line</button>
            <button onClick={handleCreate}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">Create Invoice</button>
          </div>
        </div>
      )}

      {/* Invoices Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Invoice #</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Balance</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {invoices.map((inv) => (
              <tr key={inv.id} className="hover:bg-gray-50">
                <td className="px-6 py-3 text-sm font-medium text-blue-600">{inv.invoice_number}</td>
                <td className="px-6 py-3 text-sm">{inv.customer_name}</td>
                <td className="px-6 py-3 text-sm">{formatDate(inv.issue_date)}</td>
                <td className="px-6 py-3 text-sm">{formatDate(inv.due_date)}</td>
                <td className="px-6 py-3 text-sm text-right">{formatCurrency(inv.total_amount)}</td>
                <td className="px-6 py-3 text-sm text-right font-medium">{formatCurrency(inv.balance_due)}</td>
                <td className="px-6 py-3 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(inv.status)}`}>{inv.status}</span>
                </td>
                <td className="px-6 py-3 text-center">
                  {inv.status === 'draft' && (
                    <button onClick={() => handleSend(inv.id)}
                      className="text-xs text-blue-600 hover:text-blue-800">Send</button>
                  )}
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

export default InvoicesPage;
