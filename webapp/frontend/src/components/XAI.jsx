import React, { useState, useEffect } from 'react';
import { fetchXAIList, fetchXAIExplanation } from '../api';
import { Search, BrainCircuit, CheckCircle2, AlertCircle, Lightbulb, Loader2 } from 'lucide-react';

const XAI = () => {
  const [outletList, setOutletList] = useState([]);
  const [selectedOutlet, setSelectedOutlet] = useState('');
  const [search, setSearch] = useState('');
  
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Initial load of available outlets
  useEffect(() => {
    fetchXAIList()
      .then(list => {
        setOutletList(list);
        if (list.length > 0) setSelectedOutlet(list[0]);
      })
      .catch(console.error);
  }, []);

  // Fetch explanation when outlet changes
  useEffect(() => {
    if (!selectedOutlet) return;
    setLoading(true);
    setError('');
    fetchXAIExplanation(selectedOutlet)
      .then(res => {
        setExplanation(res);
        setLoading(false);
      })
      .catch(err => {
        setError('Failed to load explanation for this outlet.');
        setLoading(false);
      });
  }, [selectedOutlet]);

  const filteredList = outletList.filter(id => id.includes(search)).slice(0, 50); // Limit to 50 for perf in dropdown

  return (
    <div className="space-y-6">
      {/* Top Search Bar */}
      <div className="glass-card p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <BrainCircuit className="text-purple-400 w-6 h-6" />
            Outlet-Level AI Reasoning
          </h2>
          <p className="text-sm text-slate-400 mt-1">Deep dive into the machine learning drivers behind each allocation.</p>
        </div>
        
        <div className="relative w-full md:w-72">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search Outlet ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-slate-900/50 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 outline-none focus:border-purple-500"
          />
          {search && filteredList.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 max-h-60 overflow-y-auto bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50">
              {filteredList.map(id => (
                <button
                  key={id}
                  onClick={() => {
                    setSelectedOutlet(id);
                    setSearch('');
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-slate-100"
                >
                  {id}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="flex items-center justify-center h-64 glass-card">
          <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
        </div>
      ) : error ? (
        <div className="glass-card p-8 text-center text-red-400 border-red-500/20">{error}</div>
      ) : explanation ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column: Stats & Business Summary */}
          <div className="lg:col-span-2 space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="glass-card p-5 bg-gradient-to-br from-slate-800/80 to-slate-900/80 border-t-4 border-t-blue-500">
                <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Predicted Potential</p>
                <p className="text-2xl font-bold text-slate-100 mt-2">{explanation.Predicted_Potential?.toLocaleString()} L</p>
              </div>
              <div className="glass-card p-5 bg-gradient-to-br from-slate-800/80 to-slate-900/80 border-t-4 border-t-purple-500">
                <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Model Confidence</p>
                <p className="text-2xl font-bold text-slate-100 mt-2">
                  {explanation.Confidence_Level > 1 
                    ? (explanation.Confidence_Level).toFixed(1) + '%' 
                    : (explanation.Confidence_Level * 100).toFixed(1) + '%'}
                </p>
              </div>
              <div className="glass-card p-5 bg-gradient-to-br from-slate-800/80 to-slate-900/80 border-t-4 border-t-indigo-500">
                <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Outlet Segment</p>
                <p className="text-lg font-bold text-slate-100 mt-2 truncate">{explanation.Segment}</p>
              </div>
            </div>

            <div className="glass-card p-6">
              <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <BrainCircuit className="w-5 h-5 text-purple-400" />
                Business Explanation
              </h3>
              <p className="text-slate-300 leading-relaxed text-lg">
                {explanation.Business_Explanation}
              </p>
            </div>
            
            <div className="glass-card p-6 bg-blue-500/5 border border-blue-500/20">
              <h3 className="text-lg font-semibold text-blue-400 mb-4 flex items-center gap-2">
                <Lightbulb className="w-5 h-5" />
                Recommended Action
              </h3>
              <p className="text-slate-200 font-medium text-lg">
                {explanation.Recommended_Action}
              </p>
            </div>
          </div>

          {/* Right Column: Drivers */}
          <div className="space-y-6">
            <div className="glass-card p-6 border-t-4 border-t-emerald-500 h-full">
              <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                Key Positive Drivers
              </h3>
              <div className="space-y-3">
                {explanation.Top_Positive_Drivers ? String(explanation.Top_Positive_Drivers).split(',').map((driver, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                    <span className="text-emerald-400 font-bold">•</span>
                    <span className="text-sm text-slate-300 capitalize">{driver.trim().replace(/_/g, ' ')}</span>
                  </div>
                )) : <p className="text-slate-500 text-sm">No significant positive drivers.</p>}
              </div>
            </div>

            <div className="glass-card p-6 border-t-4 border-t-pink-500 h-full">
              <h3 className="text-lg font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-pink-400" />
                Key Negative Drivers
              </h3>
              <div className="space-y-3">
                {explanation.Top_Negative_Drivers ? String(explanation.Top_Negative_Drivers).split(',').map((driver, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-pink-500/5 border border-pink-500/10">
                    <span className="text-pink-400 font-bold">•</span>
                    <span className="text-sm text-slate-300 capitalize">{driver.trim().replace(/_/g, ' ')}</span>
                  </div>
                )) : <p className="text-slate-500 text-sm">No significant negative drivers.</p>}
              </div>
            </div>
          </div>
          
        </div>
      ) : (
        <div className="glass-card p-12 text-center text-slate-400">
          Select an outlet to view its AI explanation.
        </div>
      )}
    </div>
  );
};

export default XAI;
