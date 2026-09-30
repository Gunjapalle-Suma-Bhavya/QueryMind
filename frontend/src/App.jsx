import React, { useState, useEffect } from 'react';
import { 
  Database, Sparkles, Sliders, ShieldCheck, AlertTriangle, 
  BarChart3, BookOpen, Layers, CheckCircle2, GitBranch, Key, RefreshCw, Server
} from 'lucide-react';
import ChatAssistant from './components/ChatAssistant';
import BenchmarkLab from './components/BenchmarkLab';
import ClassificationRegistry from './components/ClassificationRegistry';
import FailureArchitecture from './components/FailureArchitecture';
import ApiKeyModal from './components/ApiKeyModal';

export default function App() {
  const [activeTab, setActiveTab] = useState('assistant');
  const [mode, setMode] = useState('guided'); // 'guided' or 'baseline'
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [config, setConfig] = useState(null);
  const [backendOnline, setBackendOnline] = useState(null);

  const loadConfig = async () => {
    try {
      const res = await fetch('/api/config');
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
        setBackendOnline(true);
      } else {
        setBackendOnline(false);
      }
    } catch (err) {
      setBackendOnline(false);
    }
  };

  useEffect(() => {
    loadConfig();
    const interval = setInterval(loadConfig, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col selection:bg-sky-500 selection:text-white">
      {/* Top Warning Banner if Backend is Offline */}
      {backendOnline === false && (
        <div className="bg-amber-500/15 border-b border-amber-500/30 px-4 py-2.5 text-xs text-amber-200 flex items-center justify-between">
          <div className="flex items-center gap-2 max-w-5xl mx-auto w-full">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Backend Server Offline:</strong> Cannot reach API at <code className="bg-slate-900 px-1 py-0.5 rounded text-amber-300">http://localhost:8000</code>. To start it, run <code className="bg-slate-900 px-1.5 py-0.5 rounded text-amber-300 font-bold">python run.py</code> or <code className="bg-slate-900 px-1.5 py-0.5 rounded text-amber-300 font-bold">./start.sh</code> in your terminal.
            </span>
          </div>
          <button 
            onClick={loadConfig}
            className="text-[11px] bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 px-2.5 py-1 rounded-md border border-amber-500/40 transition-all ml-3 shrink-0"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Top Navigation Bar */}
      <header className="border-b border-slate-800/80 bg-slate-900/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          {/* Brand Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-blue-500 flex items-center justify-center shadow-lg shadow-sky-500/20 text-white">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-white tracking-tight">QueryMind</span>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
                  Enterprise
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium hidden sm:block">
                Natural Language to SQL with Ambiguity Clarification Engine
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('assistant')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
                activeTab === 'assistant'
                  ? 'bg-slate-800 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
              <span>Query Assistant</span>
            </button>

            <button
              onClick={() => setActiveTab('benchmark')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
                activeTab === 'benchmark'
                  ? 'bg-slate-800 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5 text-indigo-400" />
              <span>50-Query Benchmark</span>
            </button>

            <button
              onClick={() => setActiveTab('registry')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
                activeTab === 'registry'
                  ? 'bg-slate-800 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
              <span>Classification Rules</span>
            </button>

            <button
              onClick={() => setActiveTab('architecture')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all ${
                activeTab === 'architecture'
                  ? 'bg-slate-800 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5 text-amber-400" />
              <span>Failure Analysis</span>
            </button>
          </nav>

          {/* Right Action: API Keys & Connection Status */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setShowKeyModal(true)}
              className="px-3 py-1.5 rounded-xl bg-slate-800/90 hover:bg-slate-750 text-slate-200 hover:text-white border border-slate-700/80 text-xs font-medium flex items-center gap-2 shadow-sm transition-all"
              title="Configure API Keys, LLM Provider or Offline Mode"
            >
              <Key className="w-3.5 h-3.5 text-sky-400" />
              <span className="hidden sm:inline">API Keys & Engine</span>
              <span className={`w-2 h-2 rounded-full ${backendOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
            </button>
          </div>
        </div>

        {/* Mobile Nav Tabs */}
        <div className="md:hidden flex items-center justify-around border-t border-slate-800/80 px-2 py-1.5 bg-slate-950">
          <button
            onClick={() => setActiveTab('assistant')}
            className={`px-2 py-1 rounded-lg text-xs font-medium ${activeTab === 'assistant' ? 'text-sky-400 font-bold' : 'text-slate-400'}`}
          >
            Assistant
          </button>
          <button
            onClick={() => setActiveTab('benchmark')}
            className={`px-2 py-1 rounded-lg text-xs font-medium ${activeTab === 'benchmark' ? 'text-indigo-400 font-bold' : 'text-slate-400'}`}
          >
            50-Benchmark
          </button>
          <button
            onClick={() => setActiveTab('registry')}
            className={`px-2 py-1 rounded-lg text-xs font-medium ${activeTab === 'registry' ? 'text-emerald-400 font-bold' : 'text-slate-400'}`}
          >
            Rules
          </button>
          <button
            onClick={() => setActiveTab('architecture')}
            className={`px-2 py-1 rounded-lg text-xs font-medium ${activeTab === 'architecture' ? 'text-amber-400 font-bold' : 'text-slate-400'}`}
          >
            Architecture
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'assistant' && (
          <ChatAssistant 
            mode={mode} 
            setMode={setMode} 
            config={config} 
            backendOnline={backendOnline} 
            onOpenSettings={() => setShowKeyModal(true)} 
          />
        )}
        {activeTab === 'benchmark' && (
          <BenchmarkLab />
        )}
        {activeTab === 'registry' && (
          <ClassificationRegistry onSelectQuery={(q) => { setActiveTab('assistant'); }} />
        )}
        {activeTab === 'architecture' && (
          <FailureArchitecture />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-900/50 py-6 mt-12 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-400">QueryMind</span>
            <span>—</span>
            <span>Enterprise Semantic Clarification & 50-Query Benchmark Suite</span>
          </div>

          <div className="flex items-center gap-4 text-slate-400">
            <span className="flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Fast & Verified (SQLite Sandbox)
            </span>
            <span>•</span>
            <span>FastAPI + React + Tailwind</span>
          </div>
        </div>
      </footer>

      {/* API Key & Engine Settings Modal */}
      <ApiKeyModal
        isOpen={showKeyModal}
        onClose={() => setShowKeyModal(false)}
        config={config}
        onConfigSaved={loadConfig}
      />
    </div>
  );
}
