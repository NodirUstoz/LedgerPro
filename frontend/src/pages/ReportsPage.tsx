/**
 * ReportsPage -- financial statement generation and saved report management.
 */

import React, { useCallback, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import {
  fetchIncomeStatement,
  fetchBalanceSheet,
  fetchCashFlow,
  fetchSavedReports,
  clearReport,
} from '../store/reportSlice';
import { formatCurrency, formatDate } from '../utils/formatters';

type ReportTab = 'income_statement' | 'balance_sheet' | 'cash_flow' | 'saved';

const ReportsPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const companyId = useAppSelector((s) => s.auth.user?.last_active_company) || '';
  const { incomeStatement, balanceSheet, cashFlow, savedReports, statementLoading } =
    useAppSelector((s) => s.reports);

  const [activeTab, setActiveTab] = useState<ReportTab>('income_statement');
  const [startDate, setStartDate] = useState(`${new Date().getFullYear()}-01-01`);
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().split('T')[0]);
  const [comparePrior, setComparePrior] = useState(false);

  const generateReport = useCallback(() => {
    if (!companyId) return;
    dispatch(clearReport());

    switch (activeTab) {
      case 'income_statement':
        dispatch(fetchIncomeStatement({
          company: companyId, start_date: startDate, end_date: endDate,
          compare_prior_period: comparePrior ? 'true' : undefined,
        }));
        break;
      case 'balance_sheet':
        dispatch(fetchBalanceSheet({ company: companyId, as_of_date: asOfDate }));
        break;
      case 'cash_flow':
        dispatch(fetchCashFlow({ company: companyId, start_date: startDate, end_date: endDate }));
        break;
      case 'saved':
        dispatch(fetchSavedReports({ company: companyId }));
        break;
    }
  }, [dispatch, companyId, activeTab, startDate, endDate, asOfDate, comparePrior]);

  const tabs: Array<{ key: ReportTab; label: string }> = [
    { key: 'income_statement', label: 'Income Statement' },
    { key: 'balance_sheet', label: 'Balance Sheet' },
    { key: 'cash_flow', label: 'Cash Flow' },
    { key: 'saved', label: 'Saved Reports' },
  ];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Financial Reports</h1>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button key={tab.key}
              onClick={() => { setActiveTab(tab.key); dispatch(clearReport()); }}
              className={`py-3 px-1 border-b-2 text-sm font-medium ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Date Controls */}
      <div className="flex gap-4 items-end">
        {activeTab === 'balance_sheet' ? (
          <div>
            <label className="block text-sm text-gray-600 mb-1">As of Date</label>
            <input type="date" value={asOfDate} onChange={(e) => setAsOfDate(e.target.value)}
              className="px-3 py-2 border rounded-lg" />
          </div>
        ) : activeTab !== 'saved' ? (
          <>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Start Date</label>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
                className="px-3 py-2 border rounded-lg" />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">End Date</label>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
                className="px-3 py-2 border rounded-lg" />
            </div>
            {activeTab === 'income_statement' && (
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={comparePrior}
                  onChange={(e) => setComparePrior(e.target.checked)}
                  className="rounded" />
                Compare prior period
              </label>
            )}
          </>
        ) : null}
        <button onClick={generateReport}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          disabled={statementLoading}>
          {statementLoading ? 'Generating...' : 'Generate'}
        </button>
      </div>

      {/* Income Statement */}
      {activeTab === 'income_statement' && incomeStatement && (
        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          <h2 className="text-xl font-bold text-center">Income Statement</h2>
          <p className="text-center text-gray-500">
            {incomeStatement.company} | {formatDate(incomeStatement.period_start)} to {formatDate(incomeStatement.period_end)}
          </p>
          <div className="space-y-4">
            <h3 className="font-semibold text-green-700 border-b pb-1">Revenue</h3>
            {incomeStatement.revenue.items.map((item, i) => (
              <div key={i} className="flex justify-between pl-4">
                <span className="text-sm">{item.account_code} - {item.account_name}</span>
                <span className="text-sm font-medium">{formatCurrency(item.amount)}</span>
              </div>
            ))}
            <div className="flex justify-between font-bold border-t pt-2">
              <span>Total Revenue</span>
              <span>{formatCurrency(incomeStatement.revenue.total)}</span>
            </div>

            <h3 className="font-semibold text-red-700 border-b pb-1 mt-4">Expenses</h3>
            {incomeStatement.expenses.items.map((item, i) => (
              <div key={i} className="flex justify-between pl-4">
                <span className="text-sm">{item.account_code} - {item.account_name}</span>
                <span className="text-sm font-medium">{formatCurrency(item.amount)}</span>
              </div>
            ))}
            <div className="flex justify-between font-bold border-t pt-2">
              <span>Total Expenses</span>
              <span>{formatCurrency(incomeStatement.expenses.total)}</span>
            </div>

            <div className="flex justify-between font-bold text-lg border-t-2 border-gray-800 pt-3 mt-4">
              <span>Net Income</span>
              <span className={parseFloat(incomeStatement.net_income) >= 0 ? 'text-green-700' : 'text-red-700'}>
                {formatCurrency(incomeStatement.net_income)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Balance Sheet */}
      {activeTab === 'balance_sheet' && balanceSheet && (
        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          <h2 className="text-xl font-bold text-center">Balance Sheet</h2>
          <p className="text-center text-gray-500">
            {balanceSheet.company} | As of {formatDate(balanceSheet.as_of_date)}
          </p>
          {(['assets', 'liabilities', 'equity'] as const).map((section) => (
            <div key={section} className="space-y-2">
              <h3 className="font-semibold border-b pb-1 capitalize">{section}</h3>
              {balanceSheet[section].items.map((item, i) => (
                <div key={i} className="flex justify-between pl-4">
                  <span className="text-sm">{item.account_code} - {item.account_name}</span>
                  <span className="text-sm">{formatCurrency(item.balance)}</span>
                </div>
              ))}
              <div className="flex justify-between font-bold border-t pt-1">
                <span>Total {section}</span>
                <span>{formatCurrency(balanceSheet[section].total)}</span>
              </div>
            </div>
          ))}
          <div className="flex justify-between font-bold text-lg border-t-2 pt-3">
            <span>Balanced</span>
            <span className={balanceSheet.is_balanced ? 'text-green-700' : 'text-red-700'}>
              {balanceSheet.is_balanced ? 'Yes' : 'No'}
            </span>
          </div>
        </div>
      )}

      {/* Cash Flow */}
      {activeTab === 'cash_flow' && cashFlow && (
        <div className="bg-white rounded-lg shadow p-6 space-y-4">
          <h2 className="text-xl font-bold text-center">Cash Flow Statement</h2>
          <p className="text-center text-gray-500">
            {cashFlow.company} | {formatDate(cashFlow.period_start)} to {formatDate(cashFlow.period_end)}
          </p>
          {[
            { label: 'Operating Activities', value: cashFlow.operating_activities.total },
            { label: 'Investing Activities', value: cashFlow.investing_activities.total },
            { label: 'Financing Activities', value: cashFlow.financing_activities.total },
          ].map(({ label, value }) => (
            <div key={label} className="flex justify-between py-2 border-b">
              <span>{label}</span>
              <span className="font-medium">{formatCurrency(value)}</span>
            </div>
          ))}
          <div className="flex justify-between font-bold text-lg pt-2">
            <span>Net Change in Cash</span>
            <span>{formatCurrency(cashFlow.net_change_in_cash)}</span>
          </div>
          <div className="flex justify-between pt-1">
            <span>Opening Balance</span>
            <span>{formatCurrency(cashFlow.opening_cash_balance)}</span>
          </div>
          <div className="flex justify-between font-bold text-lg border-t-2 pt-2">
            <span>Closing Cash Balance</span>
            <span>{formatCurrency(cashFlow.closing_cash_balance)}</span>
          </div>
        </div>
      )}

      {/* Saved Reports */}
      {activeTab === 'saved' && savedReports.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {savedReports.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 text-sm font-medium">{r.name}</td>
                  <td className="px-6 py-3 text-sm">{r.report_type_display}</td>
                  <td className="px-6 py-3 text-sm">
                    {r.period_start && r.period_end
                      ? `${formatDate(r.period_start)} - ${formatDate(r.period_end)}`
                      : '--'}
                  </td>
                  <td className="px-6 py-3 text-sm">{formatDate(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ReportsPage;
