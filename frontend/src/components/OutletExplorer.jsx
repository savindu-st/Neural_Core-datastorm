import React, { useState, useEffect } from 'react';
import { fetchOutlets, fetchFilters } from '../api';
import { Search, Loader2 } from 'lucide-react';

const OutletExplorer = () => {
  const [outlets, setOutlets] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  
  const [filters, setFilters] = useState({ provinces: [], distributors: [] });
  const [selectedProvince, setSelectedProvince] = useState('All');
  const [selectedDistributor, setSelectedDistributor] = useState('All');
  const [search, setSearch] = useState('');
  
  const [page, setPage] = useState(0);
  const limit = 50;

  useEffect(() => {
    fetchFilters().then(setFilters).catch(console.error);
  }, []);

  useEffect(() => {
    setLoading(true);
    fetchOutlets(limit, page * limit, selectedProvince, selectedDistributor, search)
      .then(res => {
        setOutlets(res.items);
        setTotal(res.total);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [page, selectedProvince, selectedDistributor, search]);

  return (
    <div className="space-y-6 h-[calc(100vh-140px)] flex flex-col">
      <div className="glass-card p-6 flex flex-wrap gap-4 items-center justify-between shrink-0">
        <div className="flex gap-4 flex-wrap">
          <div className="flex flex-col">
            <label className="text-xs text-slate-400 mb-1">Province</label>
            <select 
              className="bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500"
              value={selectedProvince}
              onChange={e => { setSelectedProvince(e.target.value); setPage(0); }}
            >
              {filters.provinces.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          
          <div className="flex flex-col">
            <label className="text-xs text-slate-400 mb-1">Distributor</label>
            <select 
              className="bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 outline-none focus:border-blue-500"
              value={selectedDistributor}
              onChange={e => { setSelectedDistributor(e.target.value); setPage(0); }}
            >
              {filters.distributors.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
        </div>

        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
          <input 
            type="text"
            placeholder="Search Outlet ID..."
            className="bg-slate-900/50 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 outline-none focus:border-blue-500 w-64"
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(0); }}
          />
        </div>
      </div>

      <div className="glass-card flex-1 overflow-hidden flex flex-col">
        <div className="overflow-y-auto flex-1 p-0">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead className="bg-slate-800/80 sticky top-0 backdrop-blur-sm z-10">
                <tr>
                  <th className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700/50">Outlet ID</th>
                  <th className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700/50">Province</th>
                  <th className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700/50">Distributor</th>
                  <th className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700/50">Current Sales (L)</th>
                  <th className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700/50">Potential (L)</th>
                  <th className="p-4 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-700/50">Segment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/30">
                {outlets.map((outlet, i) => (
                  <tr key={i} className="hover:bg-slate-800/40 transition-colors">
                    <td className="p-4 text-sm font-medium text-slate-200">{outlet.Outlet_ID}</td>
                    <td className="p-4 text-sm text-slate-400">{outlet.Province || '-'}</td>
                    <td className="p-4 text-sm text-slate-400">{outlet.Distributor_ID || '-'}</td>
                    <td className="p-4 text-sm text-slate-400">{outlet.avg_monthly_liters ? outlet.avg_monthly_liters.toFixed(0) : '-'}</td>
                    <td className="p-4 text-sm font-medium text-blue-400">{outlet.Maximum_Monthly_Liters ? outlet.Maximum_Monthly_Liters.toFixed(0) : '-'}</td>
                    <td className="p-4 text-sm">
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        {outlet.outlet_segment || 'Unknown'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        
        {/* Pagination */}
        <div className="p-4 border-t border-slate-700/50 flex items-center justify-between bg-slate-800/30 shrink-0">
          <p className="text-sm text-slate-400">
            Showing <span className="font-medium text-slate-200">{page * limit + 1}</span> to <span className="font-medium text-slate-200">{Math.min((page + 1) * limit, total)}</span> of <span className="font-medium text-slate-200">{total}</span> outlets
          </p>
          <div className="flex gap-2">
            <button 
              className="px-3 py-1 rounded-lg border border-slate-600 text-sm text-slate-300 hover:bg-slate-700 disabled:opacity-50"
              disabled={page === 0}
              onClick={() => setPage(p => p - 1)}
            >
              Previous
            </button>
            <button 
              className="px-3 py-1 rounded-lg border border-slate-600 text-sm text-slate-300 hover:bg-slate-700 disabled:opacity-50"
              disabled={(page + 1) * limit >= total}
              onClick={() => setPage(p => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default OutletExplorer;
