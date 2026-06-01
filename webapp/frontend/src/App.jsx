import React, { useState } from 'react';
import { LayoutDashboard, MapPin, BadgeDollarSign, Sparkles, Database, Menu } from 'lucide-react';
import Overview from './components/Overview';
import OutletExplorer from './components/OutletExplorer';
import XAI from './components/XAI';
import Budget from './components/Budget';
import Quality from './components/Quality';

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [isSidebarOpen, setSidebarOpen] = useState(true);

  const tabs = [
    { id: 'overview', name: 'Executive Overview', icon: LayoutDashboard },
    { id: 'explorer', name: 'Outlet Explorer', icon: MapPin },
    { id: 'budget', name: 'Budget Allocation', icon: BadgeDollarSign },
    { id: 'xai', name: 'XAI Explanation', icon: Sparkles },
    { id: 'quality', name: 'Data Quality Evidence', icon: Database },
  ];

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden text-slate-100">
      {/* Sidebar */}
      <aside className={`transition-all duration-300 ${isSidebarOpen ? 'w-64' : 'w-20'} bg-slate-900/40 backdrop-blur-3xl border-r border-slate-800/80 flex flex-col z-50`}>
        <div className="p-5 flex items-center justify-between border-b border-slate-800/80">
          {isSidebarOpen && <span className="font-extrabold text-2xl tracking-tight gradient-text whitespace-nowrap">QuadNova</span>}
          <button onClick={() => setSidebarOpen(!isSidebarOpen)} className="p-2 rounded-xl hover:bg-slate-800/50 transition-colors">
            <Menu className="w-5 h-5 text-slate-300" />
          </button>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all duration-200 group ${
                  isActive 
                    ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 text-blue-400 border border-blue-500/30 shadow-lg shadow-blue-500/10' 
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`}
              >
                <Icon className={`w-5 h-5 ${isActive ? 'text-blue-400' : 'text-slate-400 group-hover:text-slate-200'}`} />
                {isSidebarOpen && <span className="font-medium">{tab.name}</span>}
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto bg-transparent relative">
        <header className="px-8 py-10">
          <h1 className="text-4xl font-extrabold tracking-tight text-white mb-2">
            {tabs.find(t => t.id === activeTab)?.name}
          </h1>
          <p className="text-slate-400 text-lg">QuadNova Predictive Intelligence</p>
        </header>

        <div className="px-8 pb-12 relative z-10">
          {activeTab === 'overview' && <Overview />}
          {activeTab === 'explorer' && <OutletExplorer />}
          {activeTab === 'budget' && <Budget />}
          {activeTab === 'xai' && <XAI />}
          {activeTab === 'quality' && <Quality />}
        </div>
      </main>
    </div>
  );
}

export default App;
