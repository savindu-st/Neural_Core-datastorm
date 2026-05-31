import React, { useEffect, useState } from 'react';
import { fetchBudget } from '../api';
import { Loader2, BadgeDollarSign, Store, TrendingUp, Sparkles } from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from 'recharts';

const Budget = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBudget().then(res => {
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

  if (!data || data.error) {
    return <div className="text-red-400 glass-card p-6">Failed to load budget data.</div>;
  }

  const { summary, top_outlets } = data;

  const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#ec4899', '#f59e0b'];

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="glass-card p-6 flex flex-col justify-center space-y-2">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-3 rounded-2xl border text-emerald-400 bg-emerald-500/10 border-emerald-500/20 shadow-lg backdrop-blur-md">
              <BadgeDollarSign className="w-6 h-6" strokeWidth={2.5} />
            </div>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Total Budget</p>
          </div>
          <p className="text-3xl font-extrabold text-white tracking-tight">LKR {summary.total_budget.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
        </div>

        <div className="glass-card p-6 flex flex-col justify-center space-y-2">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-3 rounded-2xl border text-blue-400 bg-blue-500/10 border-blue-500/20 shadow-lg backdrop-blur-md">
              <Store className="w-6 h-6" strokeWidth={2.5} />
            </div>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Funded Outlets</p>
          </div>
          <p className="text-3xl font-extrabold text-white tracking-tight">{summary.total_outlets.toLocaleString()}</p>
        </div>

        <div className="glass-card p-6 flex flex-col justify-center space-y-2">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-3 rounded-2xl border text-purple-400 bg-purple-500/10 border-purple-500/20 shadow-lg backdrop-blur-md">
              <TrendingUp className="w-6 h-6" strokeWidth={2.5} />
            </div>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Avg / Outlet</p>
          </div>
          <p className="text-3xl font-extrabold text-white tracking-tight">LKR {summary.avg_allocation.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
        </div>

        <div className="glass-card p-6 flex flex-col justify-center space-y-2">
          <div className="flex items-center space-x-3 mb-2">
            <div className="p-3 rounded-2xl border text-amber-400 bg-amber-500/10 border-amber-500/20 shadow-lg backdrop-blur-md">
              <Sparkles className="w-6 h-6" strokeWidth={2.5} />
            </div>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Expected Incremental</p>
          </div>
          <p className="text-3xl font-extrabold text-white tracking-tight">{summary.expected_incremental.toLocaleString(undefined, {maximumFractionDigits: 0})} L</p>
        </div>
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
              <XAxis 
                dataKey="Outlet_ID" 
                stroke="#64748b" 
                tick={{fontSize: 10, fill: '#64748b'}} 
                axisLine={false} 
                tickLine={false}
                angle={-45}
                textAnchor="end"
              />
              <YAxis stroke="#64748b" tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} />
              <Tooltip 
                contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', backdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)' }} 
                itemStyle={{ color: '#fff', fontWeight: 600 }} 
                cursor={{ fill: 'rgba(255,255,255,0.05)' }} 
              />
              <Bar dataKey="Trade_Spend_Allocation_LKR" name="Allocation (LKR)" radius={[6, 6, 0, 0]}>
                {top_outlets.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default Budget;
