import React from 'react';
import { Database, AlertTriangle, CheckCircle2, FileSearch, ShieldCheck } from 'lucide-react';

const Quality = () => {
  const issues = [
    { title: 'Missing Coordinates', desc: 'Outlets with invalid or missing Lat/Long inputs.', count: '12 Records', color: 'rose' },
    { title: 'Extreme Sales Anomalies', desc: 'Outlets exceeding historical variance thresholds (Z-score > 3).', count: '31 Records', color: 'amber' },
    { title: 'Duplicate Outlet IDs', desc: 'Records with the same Outlet_ID detected and deduplicated.', count: '15 Records', color: 'amber' },
  ];

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
              <p className="text-3xl font-extrabold text-white">4,850</p>
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
              <p className="text-3xl font-extrabold text-white">4,792</p>
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
              <p className="text-3xl font-extrabold text-white">58</p>
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
          {issues.map((issue, i) => (
            <div key={i} className="flex items-center justify-between p-5 rounded-2xl bg-slate-800/50 border border-slate-700/40 hover:border-slate-600/60 transition-colors">
              <div className="flex items-start gap-4">
                <FileSearch className="text-slate-400 w-5 h-5 mt-0.5 shrink-0" />
                <div>
                  <p className="font-semibold text-slate-200">{issue.title}</p>
                  <p className="text-sm text-slate-400 mt-0.5">{issue.desc}</p>
                </div>
              </div>
              <span className={`ml-6 shrink-0 px-3 py-1 rounded-full text-sm font-semibold ${
                issue.color === 'rose'
                  ? 'bg-rose-500/20 text-rose-400'
                  : 'bg-amber-500/20 text-amber-400'
              }`}>
                {issue.count}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Quality Score */}
      <div className="glass-card p-8 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 border-indigo-500/20">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h3 className="text-xl font-bold text-white mb-1">Overall Data Quality Score</h3>
            <p className="text-slate-400">Based on completeness, accuracy, and consistency metrics.</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-6xl font-extrabold gradient-text">98.8%</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Quality;
