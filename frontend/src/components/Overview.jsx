import React, { useEffect, useState } from 'react';
import { fetchOverview } from '../api';
import { Store, TrendingUp, Wallet, ShieldCheck, Loader2 } from 'lucide-react';
import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar, Cell } from 'recharts';

const Overview = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOverview().then(res => {
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
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    );
  }

  if (!data || data.error) {
    return <div className="text-red-400 glass-card p-6">Failed to load data. Ensure API is running.</div>;
  }

  const { metrics, segments, scatter_data } = data;

  const segmentData = Object.keys(segments).map(key => ({
    name: key,
    value: segments[key]
  }));

  const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899'];

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard title="Total Outlets" value={metrics.total_outlets.toLocaleString()} icon={Store} color="blue" />
        <MetricCard title="Avg Potential" value={`${metrics.avg_potential.toLocaleString(undefined, {maximumFractionDigits: 0})} L`} icon={TrendingUp} color="purple" />
        <MetricCard title="Allocated Budget" value={`LKR ${metrics.total_budget.toLocaleString(undefined, {maximumFractionDigits: 0})}`} icon={Wallet} color="emerald" />
        <MetricCard title="Avg Confidence" value={`${(metrics.avg_confidence * 100).toFixed(1)}%`} icon={ShieldCheck} color="pink" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scatter Chart */}
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold mb-4 text-slate-200">Potential vs Current Sales</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} opacity={0.3} />
                <XAxis type="number" dataKey="avg_monthly_liters" name="Current Sales" stroke="#64748b" tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} />
                <YAxis type="number" dataKey="Maximum_Monthly_Liters" name="Potential" stroke="#64748b" tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} />
                <Tooltip cursor={{ strokeDasharray: '3 3', stroke: '#475569' }} contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)' }} itemStyle={{ color: '#fff', fontWeight: 600 }} />
                <Scatter name="Outlets" data={scatter_data} fill="#8b5cf6" opacity={0.7} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bar Chart */}
        <div className="glass-card p-6">
          <h3 className="text-lg font-semibold mb-4 text-slate-200">Outlet Distribution by Segment</h3>
          <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={segmentData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} opacity={0.3} />
                <XAxis dataKey="name" stroke="#64748b" tick={{fontSize: 11, fill: '#64748b'}} axisLine={false} tickLine={false} />
                <YAxis stroke="#64748b" tick={{fontSize: 12, fill: '#64748b'}} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.8)', backdropFilter: 'blur(12px)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '16px', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)' }} itemStyle={{ color: '#fff', fontWeight: 600 }} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {segmentData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};

const MetricCard = ({ title, value, icon: Icon, color }) => {
  const colorMap = {
    blue: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
    purple: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
    emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    pink: 'text-pink-400 bg-pink-500/10 border-pink-500/20',
  };

  return (
    <div className="glass-card p-6 flex flex-col justify-center space-y-2">
      <div className="flex items-center space-x-3 mb-2">
        <div className={`p-3 rounded-2xl border ${colorMap[color]} shadow-lg backdrop-blur-md`}>
          <Icon className="w-6 h-6" strokeWidth={2.5} />
        </div>
        <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">{title}</p>
      </div>
      <p className="text-4xl font-extrabold text-white tracking-tight">{value}</p>
    </div>
  );
};

export default Overview;
