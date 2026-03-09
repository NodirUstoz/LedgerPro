/**
 * TaxPage -- tax rate management, tax calculator, and filing management.
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store';
import {
  fetchTaxRates,
  fetchTaxFilings,
  calculateTax,
  calculateFiling,
  fileTaxReturn,
  clearCalculation,
} from '../store/taxSlice';
import { taxRatesApi, taxFilingsApi } from '../api/tax';
import { formatCurrency, formatDate, formatPercent, statusColor } from '../utils/formatters';

type TaxTab = 'rates' | 'calculator' | 'filings';

const TaxPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const companyId = useAppSelector((s) => s.auth.user?.last_active_company) || '';
  const { taxRates, filings, calculationResult, loading } = useAppSelector((s) => s.tax);

  const [activeTab, setActiveTab] = useState<TaxTab>('rates');
  const [showCreateRate, setShowCreateRate] = useState(false);

  // Calculator state
  const [calcAmount, setCalcAmount] = useState('');
  const [calcRateId, setCalcRateId] = useState('');
  const [calcInclusive, setCalcInclusive] = useState(false);

  // Rate form
  const [rateForm, setRateForm] = useState({
    name: '', code: '', tax_type: 'sales_tax', rate: '',
    applies_to: 'both', is_inclusive: false,
  });

  const loadData = useCallback(() => {
    if (!companyId) return;
    dispatch(fetchTaxRates({ company: companyId }));
    dispatch(fetchTaxFilings({ company: companyId }));
  }, [dispatch, companyId]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleCreateRate = async () => {
    if (!rateForm.name || !rateForm.code || !rateForm.rate) return;
    try {
      await taxRatesApi.create({
        company: companyId,
        name: rateForm.name,
        code: rateForm.code,
        tax_type: rateForm.tax_type,
        rate: rateForm.rate,
        applies_to: rateForm.applies_to as any,
        is_inclusive: rateForm.is_inclusive,
        is_active: true,
      });
      setShowCreateRate(false);
      setRateForm({ name: '', code: '', tax_type: 'sales_tax', rate: '', applies_to: 'both', is_inclusive: false });
      loadData();
    } catch {}
  };

  const handleCalculate = () => {
    if (!calcAmount || !calcRateId) return;
    dispatch(calculateTax({
      amount: calcAmount,
      tax_rate_id: calcRateId,
      is_inclusive: calcInclusive,
    }));
  };

  const tabs: Array<{ key: TaxTab; label: string }> = [
    { key: 'rates', label: 'Tax Rates' },
    { key: 'calculator', label: 'Tax Calculator' },
    { key: 'filings', label: 'Tax Filings' },
  ];

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Tax Management</h1>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
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

      {/* Tax Rates Tab */}
      {activeTab === 'rates' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button onClick={() => setShowCreateRate(!showCreateRate)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              {showCreateRate ? 'Cancel' : 'New Tax Rate'}
            </button>
          </div>

          {showCreateRate && (
            <div className="bg-white rounded-lg shadow p-6 space-y-4">
              <h3 className="text-lg font-semibold">Create Tax Rate</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <input placeholder="Name (e.g. CA Sales Tax)" value={rateForm.name}
                  onChange={(e) => setRateForm({ ...rateForm, name: e.target.value })}
                  className="px-3 py-2 border rounded-lg" />
                <input placeholder="Code (e.g. ST-8.25)" value={rateForm.code}
                  onChange={(e) => setRateForm({ ...rateForm, code: e.target.value })}
                  className="px-3 py-2 border rounded-lg" />
                <input placeholder="Rate %" type="number" step="0.01" value={rateForm.rate}
                  onChange={(e) => setRateForm({ ...rateForm, rate: e.target.value })}
                  className="px-3 py-2 border rounded-lg" />
                <select value={rateForm.tax_type}
                  onChange={(e) => setRateForm({ ...rateForm, tax_type: e.target.value })}
                  className="px-3 py-2 border rounded-lg">
                  <option value="sales_tax">Sales Tax</option>
                  <option value="vat">VAT</option>
                  <option value="gst">GST</option>
                  <option value="withholding">Withholding</option>
                </select>
                <select value={rateForm.applies_to}
                  onChange={(e) => setRateForm({ ...rateForm, applies_to: e.target.value })}
                  className="px-3 py-2 border rounded-lg">
                  <option value="both">Both</option>
                  <option value="sales">Sales Only</option>
                  <option value="purchases">Purchases Only</option>
                </select>
              </div>
              <button onClick={handleCreateRate}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">Save</button>
            </div>
          )}

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Rate</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Applies To</th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {taxRates.map((rate) => (
                  <tr key={rate.id} className="hover:bg-gray-50">
                    <td className="px-6 py-3 text-sm font-medium">{rate.name}</td>
                    <td className="px-6 py-3 text-sm font-mono">{rate.code}</td>
                    <td className="px-6 py-3 text-sm">{rate.tax_type}</td>
                    <td className="px-6 py-3 text-sm text-right">{formatPercent(rate.rate)}</td>
                    <td className="px-6 py-3 text-sm text-center capitalize">{rate.applies_to}</td>
                    <td className="px-6 py-3 text-center">
                      <span className={`inline-block w-2 h-2 rounded-full ${rate.is_active ? 'bg-green-500' : 'bg-gray-400'}`} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tax Calculator Tab */}
      {activeTab === 'calculator' && (
        <div className="max-w-lg mx-auto bg-white rounded-lg shadow p-6 space-y-4">
          <h3 className="text-lg font-semibold">Tax Calculator</h3>
          <input type="number" step="0.01" placeholder="Enter amount" value={calcAmount}
            onChange={(e) => { setCalcAmount(e.target.value); dispatch(clearCalculation()); }}
            className="w-full px-3 py-2 border rounded-lg" />
          <select value={calcRateId} onChange={(e) => { setCalcRateId(e.target.value); dispatch(clearCalculation()); }}
            className="w-full px-3 py-2 border rounded-lg">
            <option value="">Select Tax Rate</option>
            {taxRates.filter((r) => r.is_active).map((r) => (
              <option key={r.id} value={r.id}>{r.name} ({formatPercent(r.rate)})</option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={calcInclusive}
              onChange={(e) => setCalcInclusive(e.target.checked)} className="rounded" />
            Tax-inclusive amount
          </label>
          <button onClick={handleCalculate}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Calculate
          </button>

          {calculationResult && (
            <div className="bg-gray-50 rounded-lg p-4 space-y-2 mt-4">
              <div className="flex justify-between">
                <span className="text-gray-600">Net Amount</span>
                <span className="font-medium">{formatCurrency(calculationResult.net_amount)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Tax ({calculationResult.tax_rate_name})</span>
                <span className="font-medium">{formatCurrency(calculationResult.tax_amount)}</span>
              </div>
              <div className="flex justify-between text-lg font-bold border-t pt-2">
                <span>Gross Amount</span>
                <span>{formatCurrency(calculationResult.gross_amount)}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tax Filings Tab */}
      {activeTab === 'filings' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Deadline</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount Due</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filings.map((f) => (
                <tr key={f.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 text-sm font-medium">{f.name}</td>
                  <td className="px-6 py-3 text-sm">{formatDate(f.period_start)} - {formatDate(f.period_end)}</td>
                  <td className="px-6 py-3 text-sm">{formatDate(f.filing_deadline)}</td>
                  <td className="px-6 py-3 text-sm text-right font-medium">{formatCurrency(f.total_due)}</td>
                  <td className="px-6 py-3 text-center">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${statusColor(f.status)}`}>{f.status}</span>
                  </td>
                  <td className="px-6 py-3 text-center space-x-2">
                    {(f.status === 'draft' || f.status === 'calculated') && (
                      <>
                        <button onClick={() => dispatch(calculateFiling(f.id))}
                          className="text-xs text-blue-600 hover:text-blue-800">Calculate</button>
                        <button onClick={() => dispatch(fileTaxReturn({ id: f.id }))}
                          className="text-xs text-green-600 hover:text-green-800">File</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {loading && <p className="text-center py-6 text-gray-500">Loading...</p>}
        </div>
      )}
    </div>
  );
};

export default TaxPage;
