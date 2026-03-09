/**
 * DashboardPage -- main financial overview with KPIs, charts, and recent activity.
 */

import React, { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import { useDashboardData, useCurrencyFormatter } from '../hooks/useAccounting';
import { fetchJournalEntries } from '../store/ledgerSlice';
import { fetchInvoices } from '../store/invoiceSlice';
import { fetchExpenses } from '../store/expenseSlice';
import { formatDate, statusColor } from '../utils/formatters';

interface KPICardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
}

const KPICard: React.FC<KPICardProps> = ({ title, value, subtitle, trend }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <p className="text-sm font-medium text-gray-500">{title}</p>
    <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
    {subtitle && (
      <p className={`mt-1 text-sm ${
        trend === 'up' ? 'text-green-600' :
        trend === 'down' ? 'text-red-600' : 'text-gray-500'
      }`}>
        {subtitle}
      </p>
    )}
  </div>
);

const DashboardPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const companyId = useAppSelector((s) => s.auth.user?.last_active_company) || null;
  const { invoiceSummary, expenseSummary, isLoading } = useDashboardData(companyId);
  const recentEntries = useAppSelector((s) => s.ledger.journalEntries.slice(0, 5));
  const recentInvoices = useAppSelector((s) => s.invoices.invoices.slice(0, 5));
  const recentExpenses = useAppSelector((s) => s.expenses.expenses.slice(0, 5));
  const fmt = useCurrencyFormatter();

  useEffect(() => {
    if (!companyId) return;
    dispatch(fetchJournalEntries({ company: companyId, page_size: '5' }));
    dispatch(fetchInvoices({ company: companyId, page_size: '5' }));
    dispatch(fetchExpenses({ company: companyId, page_size: '5' }));
  }, [dispatch, companyId]);

  if (!companyId) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-gray-500 text-lg">Select a company to view the dashboard.</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Financial Dashboard</h1>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Total Revenue"
          value={fmt(invoiceSummary?.total_revenue || 0)}
          subtitle="Paid invoices"
          trend="up"
        />
        <KPICard
          title="Outstanding Receivables"
          value={fmt(invoiceSummary?.total_outstanding || 0)}
          subtitle={`${invoiceSummary?.overdue || 0} overdue`}
          trend={invoiceSummary?.overdue ? 'down' : 'neutral'}
        />
        <KPICard
          title="Total Expenses"
          value={fmt(expenseSummary?.total_expenses || 0)}
          subtitle={`${expenseSummary?.count || 0} transactions`}
        />
        <KPICard
          title="Net Income"
          value={fmt(
            (parseFloat(String(invoiceSummary?.total_revenue || 0)) -
             parseFloat(String(expenseSummary?.total_expenses || 0))).toString()
          )}
          subtitle="Year to date"
          trend="up"
        />
      </div>

      {/* Recent Activity Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Invoices */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-800">Recent Invoices</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {recentInvoices.map((inv) => (
              <div key={inv.id} className="px-6 py-3 flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{inv.invoice_number}</p>
                  <p className="text-sm text-gray-500">{inv.customer_name}</p>
                </div>
                <div className="text-right">
                  <p className="font-medium">{fmt(inv.total_amount)}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(inv.status)}`}>
                    {inv.status}
                  </span>
                </div>
              </div>
            ))}
            {recentInvoices.length === 0 && (
              <p className="px-6 py-4 text-gray-500 text-sm">No recent invoices.</p>
            )}
          </div>
        </div>

        {/* Recent Expenses */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-800">Recent Expenses</h2>
          </div>
          <div className="divide-y divide-gray-100">
            {recentExpenses.map((exp) => (
              <div key={exp.id} className="px-6 py-3 flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{exp.expense_number}</p>
                  <p className="text-sm text-gray-500">{exp.vendor_name || 'No vendor'}</p>
                </div>
                <div className="text-right">
                  <p className="font-medium">{fmt(exp.total_amount)}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(exp.status)}`}>
                    {exp.status}
                  </span>
                </div>
              </div>
            ))}
            {recentExpenses.length === 0 && (
              <p className="px-6 py-4 text-gray-500 text-sm">No recent expenses.</p>
            )}
          </div>
        </div>
      </div>

      {/* Recent Journal Entries */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Recent Journal Entries</h2>
        </div>
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Entry #</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {recentEntries.map((entry) => (
              <tr key={entry.id} className="hover:bg-gray-50">
                <td className="px-6 py-3 text-sm font-medium text-blue-600">{entry.entry_number}</td>
                <td className="px-6 py-3 text-sm text-gray-700">{formatDate(entry.date)}</td>
                <td className="px-6 py-3 text-sm text-gray-700">{entry.description}</td>
                <td className="px-6 py-3 text-sm text-gray-900 text-right">{fmt(entry.total_debit)}</td>
                <td className="px-6 py-3 text-center">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(entry.status)}`}>
                    {entry.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DashboardPage;
