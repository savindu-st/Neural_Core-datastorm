import React, { useEffect, useState } from 'react';
import { fetchBudget, simulateBudget } from '../api';
import { Loader2, BadgeDollarSign, Store, TrendingUp, Sparkles, SlidersHorizontal, Play } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts';

const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b', '#06b6d4', '#f43f5e', '#a855f7'];

const Budget = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Simulator state
  const [simBudget, setSimBudget] = useState(5000000);
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);

  useEffect(() => {
    fetchBudget().then(res => {
      setData(res);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  const runSimulation = () => {
    setSimLoading(true);
    simulateBudget(simBudget).then(res => {
      setSimResult(res);
      setSimLoading(false);
    }).catch(() => setSimLoading(false));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
      </div>
    );
  }

  if (!data) {
    return <div className="text-red-400 glass-card p-6">Failed to load budget data.</div>;
  }

  const { summary, top_outlets } = data;

  const formatLKR = (v) => `LKR ${Number(v).toLocaleString(undefined, {maximumFractionDigits: 0})}`;

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Total Budget', value: formatLKR(summary.total_budget), icon: BadgeDollarSign, color: 'emerald' },
          { label: 'Funded Outlets', value: summary.total_outlets.toLocaleString(), icon: Store, color: 'blue' },
          { label: 'Avg / Outlet', value: formatLKR(summary.avg_allocation), icon: TrendingUp, color: 'purple' },
          { label: 'Expected Incremental', value: `${Number(summary.expected_incremental).toLocaleString(undefined, {maximumFractionDigits: 0})} L`, icon: Sparkles, color: 'amber' },
        ].map((card, i) => {
          const Icon = card.icon;
          return (
            <div key={i} className="glass-card p-6 flex flex-col justify-center space-y-2">
              <div className="flex items-center space-x-3 mb-2">
                <div className={`p-3 rounded-2xl border text-${card.color}-400 bg-${card.color}-500/10 border-${card.color}-500/20 shadow-lg backdrop-blur-md`}>
                  <Icon className="w-6 h-6" strokeWidth={2.5} />
                </div>
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">{card.label}</p>
              </div>
              <p className="text-3xl font-extrabold text-white tracking-tight">{card.value}</p>
            </div>
          );
        })}
      </div>

      {/* Top Outlets Chart */}
      <div className="glass-card p-8">
        <h3 className="text-xl font-bold mb-6 text-white flex items-center gap-2">
          <BadgeDollarSign className="w-6 h-6 text-emerald-400" />
          Top 20 Outlets by Budget Allocation
        </h3>
        <div className="h-[400px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={top_outlets} margin={{ top: 20, right: 20, bottom: 60, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} opacity={0.3} />
              <XAxis dataKey="Outlet_ID" stroke="#64748b" tick={{fontSize: 10, fill: '#64748b'}} axisLine={false} tickLine={false} angle={-45} textAnchor="end" />
              <YAxis stroke="#64748b" tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', backdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)' }} itemStyle={{ color: '#fff', fontWeight: 600 }} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
              <Bar dataKey="Trade_Spend_Allocation_LKR" name="Allocation (LKR)" radius={[6, 6, 0, 0]}>
                {top_outlets.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Budget Scenario Simulator */}
      <div className="glass-card p-8 border border-indigo-500/30 bg-gradient-to-br from-indigo-500/5 to-purple-500/5">
        <h3 className="text-xl font-bold mb-6 text-white flex items-center gap-3">
          <SlidersHorizontal className="w-6 h-6 text-indigo-400" />
          Budget Scenario Simulator
        </h3>
        <p className="text-slate-400 text-sm mb-6">Adjust the total budget and see how allocations change proportionally across all outlets.</p>

        <div className="flex flex-col sm:flex-row items-start sm:items-end gap-6 mb-8">
          <div className="flex-1 w-full">
            <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-3">Total Budget (LKR)</label>
            <input
              type="range"
              min={1000000}
              max={20000000}
              step={500000}
              value={simBudget}
              onChange={e => setSimBudget(Number(e.target.value))}
              className="w-full h-2 rounded-full appearance-none cursor-pointer accent-indigo-500"
              style={{ background: `linear-gradient(to right, #6366f1 ${((simBudget - 1000000) / 19000000) * 100}%, #334155 ${((simBudget - 1000000) / 19000000) * 100}%)` }}
            />
            <div className="flex justify-between mt-2 text-xs text-slate-500">
              <span>LKR 1M</span>
              <span className="text-lg font-extrabold text-indigo-400">{formatLKR(simBudget)}</span>
              <span>LKR 20M</span>
            </div>
          </div>
          <button
            onClick={runSimulation}
            disabled={simLoading}
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50 shrink-0"
          >
            {simLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5" />}
            Simulate
          </button>
        </div>

        {simResult && (
          <div className="space-y-6 animate-fade-in">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-2xl bg-slate-800/60 border border-slate-700/40 text-center">
                <p className="text-xs text-slate-400 uppercase font-bold tracking-widest">Total Budget</p>
                <p className="text-2xl font-extrabold text-indigo-400 mt-1">{formatLKR(simResult.total_budget)}</p>
              </div>
              <div className="p-4 rounded-2xl bg-slate-800/60 border border-slate-700/40 text-center">
                <p className="text-xs text-slate-400 uppercase font-bold tracking-widest">Outlets</p>
                <p className="text-2xl font-extrabold text-blue-400 mt-1">{simResult.total_outlets}</p>
              </div>
              <div className="p-4 rounded-2xl bg-slate-800/60 border border-slate-700/40 text-center">
                <p className="text-xs text-slate-400 uppercase font-bold tracking-widest">Avg / Outlet</p>
                <p className="text-2xl font-extrabold text-purple-400 mt-1">{formatLKR(simResult.avg_allocation)}</p>
              </div>
              <div className="p-4 rounded-2xl bg-slate-800/60 border border-slate-700/40 text-center">
                <p className="text-xs text-slate-400 uppercase font-bold tracking-widest">Incremental</p>
                <p className="text-2xl font-extrabold text-emerald-400 mt-1">{Number(simResult.expected_incremental).toLocaleString(undefined, {maximumFractionDigits: 0})} L</p>
              </div>
            </div>

            <div className="h-[350px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={simResult.top_outlets} margin={{ top: 20, right: 20, bottom: 60, left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} opacity={0.3} />
                  <XAxis dataKey="Outlet_ID" stroke="#64748b" tick={{fontSize: 10, fill: '#64748b'}} axisLine={false} tickLine={false} angle={-45} textAnchor="end" />
                  <YAxis stroke="#64748b" tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} />
                  <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', backdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px' }} itemStyle={{ color: '#fff', fontWeight: 600 }} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                  <Bar dataKey="Simulated_Allocation" name="Simulated (LKR)" radius={[6, 6, 0, 0]}>
                    {simResult.top_outlets.map((_, i) => (
                      <Cell key={i} fill={`hsl(${240 + i * 6}, 70%, 60%)`} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Budget;
