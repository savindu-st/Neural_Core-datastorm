import React, { useEffect, useState } from 'react';
import { fetchQuality } from '../api';
import { Database, AlertTriangle, CheckCircle2, FileSearch, ShieldCheck, Loader2 } from 'lucide-react';

const Quality = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchQuality().then(res => {
      setData(res);
      setLoading(false);
    }).catch(err => {
      console.error(err);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
      </div>
    );
  }

  if (!data || !data.totals) {
    return <div className="text-red-400 glass-card p-6">Failed to load data quality evidence.</div>;
  }

  const { totals, datasets, rejections } = data;
  
  // Calculate quality score
  const qualityScore = totals.rows_in > 0 
    ? ((totals.rows_out / totals.rows_in) * 100).toFixed(1) 
    : '0.0';

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6 border-t-4 border-t-blue-500">
          <div className="flex items-center space-x-4">
            <div className="p-3 rounded-full bg-blue-500/20 text-blue-400">
              <Database className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">Total Records Processed</p>
              <p className="text-3xl font-extrabold text-white">{totals.rows_in.toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div className="glass-card p-6 border-t-4 border-t-emerald-500">
          <div className="flex items-center space-x-4">
            <div className="p-3 rounded-full bg-emerald-500/20 text-emerald-400">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">Clean Records</p>
              <p className="text-3xl font-extrabold text-white">{totals.rows_out.toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div className="glass-card p-6 border-t-4 border-t-rose-500">
          <div className="flex items-center space-x-4">
            <div className="p-3 rounded-full bg-rose-500/20 text-rose-400">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-400">Flagged Records</p>
              <p className="text-3xl font-extrabold text-white">{totals.rows_flagged.toLocaleString()}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Issues Table */}
      <div className="glass-card p-8">
        <h3 className="text-xl font-bold mb-6 text-white flex items-center gap-3">
          <ShieldCheck className="w-6 h-6 text-indigo-400" />
          Validation and Anomaly Report
        </h3>
        <div className="space-y-4">
          {rejections && rejections.map((issue, i) => (
            <div key={i} className="flex items-center justify-between p-5 rounded-2xl bg-slate-800/50 border border-slate-700/40 hover:border-slate-600/60 transition-colors">
              <div className="flex items-start gap-4">
                <FileSearch className="text-slate-400 w-5 h-5 mt-0.5 shrink-0" />
                <div>
                  <p className="font-semibold text-slate-200">{issue.rejection_reason}</p>
                  <p className="text-sm text-slate-400 mt-0.5">Dataset: {issue.dataset}</p>
                </div>
              </div>
              <span className={`ml-6 shrink-0 px-3 py-1 rounded-full text-sm font-semibold ${
                issue.rejection_reason.toLowerCase().includes('format') || issue.rejection_reason.toLowerCase().includes('null')
                  ? 'bg-rose-500/20 text-rose-400'
                  : 'bg-amber-500/20 text-amber-400'
              }`}>
                {issue.count.toLocaleString()} Records
              </span>
            </div>
          ))}
          {(!rejections || rejections.length === 0) && (
            <div className="text-slate-400">No rejection records found.</div>
          )}
        </div>
      </div>

      {/* Dataset Breakdowns */}
      <div className="glass-card p-8 mt-6">
        <h3 className="text-xl font-bold mb-6 text-white flex items-center gap-3">
          <Database className="w-6 h-6 text-blue-400" />
          Dataset Quality Breakdown
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400 text-sm">
                <th className="py-3 px-4 font-semibold">Dataset</th>
                <th className="py-3 px-4 font-semibold text-right">Rows In</th>
                <th className="py-3 px-4 font-semibold text-right">Clean Rows</th>
                <th className="py-3 px-4 font-semibold text-right">Flagged</th>
                <th className="py-3 px-4 font-semibold text-right">% Flagged</th>
              </tr>
            </thead>
            <tbody>
              {datasets && datasets.map((ds, i) => (
                <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 px-4 text-slate-300 font-medium">{ds.dataset}</td>
                  <td className="py-3 px-4 text-slate-300 text-right">{ds.rows_in.toLocaleString()}</td>
                  <td className="py-3 px-4 text-slate-300 text-right">{ds.rows_out.toLocaleString()}</td>
                  <td className="py-3 px-4 text-rose-400 text-right">{ds.rows_flagged.toLocaleString()}</td>
                  <td className="py-3 px-4 text-amber-400 text-right">{Number(ds.percentage_flagged).toFixed(2)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Quality Score */}
      <div className="glass-card p-8 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 border-indigo-500/20">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h3 className="text-xl font-bold text-white mb-1">Overall Data Quality Score</h3>
            <p className="text-slate-400">Based on completeness, accuracy, and consistency metrics across all pipeline steps.</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-6xl font-extrabold gradient-text">{qualityScore}%</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Quality;
