import React, { useState } from 'react';
import { 
  Search, Sparkles, AlertTriangle, CheckCircle2, ChevronDown, ChevronUp, 
  Database, Clock, Sliders, ShieldCheck, HelpCircle, ArrowRight, RefreshCw, Eye, EyeOff,
  Cpu, Key, Terminal
} from 'lucide-react';

export default function ChatAssistant({ mode, setMode, config, backendOnline, onOpenSettings }) {
  const [query, setQuery] = useState("Show me last month's best customer");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [showTechDetails, setShowTechDetails] = useState(false);
  const [selectedMetric, setSelectedMetric] = useState(null);
  const [error, setError] = useState(null);

  const sampleQueries = [
    { text: "Show me last month's best customer", tag: "Superlative + Temporal" },
    { text: "Which product is our most profitable?", tag: "Financial Margin" },
    { text: "Show all churned customers", tag: "Behavioral Churn" },
    { text: "Which item has the highest return rate?", tag: "Statistical Sample" },
    { text: "Identify slow moving inventory", tag: "Excess Stock" },
    { text: "How many total customers are registered?", tag: "Control Query" }
  ];

  const handleSearch = async (overrideQuery = null, overrideMetric = null) => {
    const q = overrideQuery !== null ? overrideQuery : query;
    const metric = overrideMetric !== null ? overrideMetric : selectedMetric;
    if (!q.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: q,
          mode: mode,
          selected_metric: metric
        })
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => null);
        throw new Error(errJson?.detail || `HTTP Error ${res.status}: ${res.statusText}`);
      }
      const data = await res.json();
      setResponse(data);
    } catch (err) {
      console.error(err);
      setError(
        err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError')
          ? "Cannot connect to QueryMind backend server. Please verify the backend is running at http://localhost:8000."
          : err.message || "An unexpected error occurred while executing the query."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleMetricSwitch = (metricKey) => {
    setSelectedMetric(metricKey);
    handleSearch(query, metricKey);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Search Header Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20"></div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-sky-400" />
                Executive Natural Language Query
              </h2>
              <button
                type="button"
                onClick={onOpenSettings}
                className="text-[11px] text-slate-400 hover:text-sky-400 flex items-center gap-1.5 bg-slate-950/80 px-2.5 py-1 rounded-lg border border-slate-800 hover:border-slate-700 transition-all ml-2"
                title="Click to view or change LLM engine and API keys"
              >
                <Cpu className="w-3.5 h-3.5 text-sky-400" />
                <span className="font-mono">{config?.active_model_desc || 'Built-in Engine (Offline)'}</span>
              </button>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Ask any business question in plain English. Conversion to SQL and database execution are automated in the background.
            </p>
          </div>

          {/* Engine Mode Toggle */}
          <div className="flex items-center gap-2 bg-slate-950 p-1.5 rounded-xl border border-slate-800 self-start">
            <button
              onClick={() => { setMode('guided'); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                mode === 'guided'
                  ? 'bg-sky-500 text-white shadow-lg shadow-sky-500/25'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              With Classification Registry (Guided)
            </button>
            <button
              onClick={() => { setMode('baseline'); }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                mode === 'baseline'
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Without Classification (Baseline Flaws)
            </button>
          </div>
        </div>

        {/* Input Form */}
        <form onSubmit={(e) => { e.preventDefault(); setSelectedMetric(null); handleSearch(); }} className="relative mb-4">
          <div className="relative flex items-center">
            <Search className="absolute left-4 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Show me last month's best customer, or Who are our churned accounts?"
              className="w-full bg-slate-950 border border-slate-700/80 rounded-xl py-3.5 pl-12 pr-32 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-500 transition-all font-medium text-sm sm:text-base"
            />
            <button
              type="submit"
              disabled={loading}
              className="absolute right-2 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white px-5 py-2 rounded-lg font-semibold text-sm transition-all shadow-md shadow-sky-500/20 flex items-center gap-2 disabled:opacity-50"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : "Ask"}
            </button>
          </div>
        </form>

        {/* Error Alert Banner */}
        {error && (
          <div className="mb-4 p-4 bg-rose-950/40 border border-rose-500/40 rounded-xl text-xs text-rose-200 space-y-2.5 animate-in fade-in duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-bold text-rose-300">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>Backend Connection Error</span>
              </div>
              <button 
                onClick={() => handleSearch()}
                className="px-2.5 py-1 bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 rounded text-[11px] font-semibold border border-rose-500/40 transition-all"
              >
                Retry Query
              </button>
            </div>
            <p className="font-mono text-[11px] text-rose-300">
              {error}
            </p>
            <div className="p-3 bg-slate-950/80 rounded-lg border border-rose-900/40 text-slate-300 space-y-1.5">
              <div className="font-semibold text-slate-200">How to solve this:</div>
              <div>Run the backend server in your terminal with:</div>
              <div className="font-mono text-sky-400 bg-slate-900 px-2.5 py-1 rounded select-all font-semibold">
                python run.py &nbsp;&nbsp;OR&nbsp;&nbsp; ./start.sh
              </div>
              <div className="flex items-center gap-2 pt-1">
                <span>Or check API key configuration:</span>
                <button
                  type="button"
                  onClick={onOpenSettings}
                  className="text-sky-400 underline hover:text-sky-300 font-semibold"
                >
                  Configure API Keys / Engine
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Suggested Quick Queries */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-xs text-slate-500 font-medium">Try asking:</span>
          {sampleQueries.map((sq, i) => (
            <button
              key={i}
              type="button"
              onClick={() => {
                setQuery(sq.text);
                setSelectedMetric(null);
                handleSearch(sq.text, null);
              }}
              className="text-xs bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white px-2.5 py-1 rounded-md transition-all border border-slate-700/50 flex items-center gap-1.5"
            >
              <span>{sq.text}</span>
              <span className="text-[10px] text-sky-400 bg-sky-950/60 px-1 rounded">{sq.tag}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Response Display Section */}
      {response && (
        <div className="space-y-5 animate-in fade-in duration-300">
          
          {/* Ambiguity & Clarification Interactive Card */}
          {response.clarification?.is_ambiguous && (
            <div className="bg-gradient-to-r from-amber-950/30 via-slate-900 to-slate-900 border border-amber-500/30 rounded-2xl p-5 shadow-lg relative">
              <div className="flex items-start gap-3.5">
                <div className="p-2 bg-amber-500/10 rounded-xl text-amber-400 mt-0.5">
                  <Sliders className="w-5 h-5" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full border border-amber-500/20">
                      Ambiguity Detected & Clarified
                    </span>
                    <span className="text-xs text-slate-400">
                      Score: {(response.clarification.ambiguity_score * 100).toFixed(0)}%
                    </span>
                  </div>

                  <p className="text-sm text-slate-200 mt-2 font-medium">
                    {response.clarification.clarification_message}
                  </p>

                  {/* Ambiguity Reasons */}
                  <div className="mt-2 text-xs text-slate-400 space-y-1">
                    {response.clarification.reasons?.map((reason, idx) => (
                      <p key={idx} className="flex items-start gap-1.5">
                        <span className="text-amber-400 font-bold">•</span>
                        <span>{reason}</span>
                      </p>
                    ))}
                  </div>

                  {/* Clickable Clarification Alternative Pills */}
                  {response.clarification.options?.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-800/80">
                      <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                        <HelpCircle className="w-3.5 h-3.5 text-sky-400" />
                        Select Evaluation Criterion to Re-rank:
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {response.clarification.options.map((opt) => (
                          <button
                            key={opt.key}
                            onClick={() => handleMetricSwitch(opt.key)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                              opt.is_active
                                ? 'bg-sky-500 text-white shadow-md shadow-sky-500/25 ring-2 ring-sky-400/40'
                                : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white border border-slate-700/60'
                            }`}
                          >
                            <span>{opt.label}</span>
                            {opt.is_active && <CheckCircle2 className="w-3.5 h-3.5 text-white" />}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Executive Direct Answer Card (SQL is hidden here as requested) */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-3 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-bold uppercase tracking-wider text-sky-400 bg-sky-500/10 px-2.5 py-0.5 rounded-full border border-sky-500/20">
                    Executive Answer
                  </span>
                  <span className="text-xs font-semibold text-slate-300 bg-slate-800/90 border border-slate-700 px-2.5 py-0.5 rounded-full flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3 text-amber-400" />
                    <span>{response.model_used || config?.active_model_desc || 'Built-in Clarification Engine'}</span>
                  </span>
                  <span className="text-xs text-slate-500">
                    {response.row_count} records retrieved in {response.execution_details?.execution_time_ms}ms
                  </span>
                </div>

                {/* The conversational synthesis */}
                <div className="text-lg sm:text-xl font-medium text-slate-100 leading-relaxed">
                  {response.conversational_answer}
                </div>

                {mode === 'baseline' && response.execution_details?.baseline_vulnerability && (
                  <div className="p-3 bg-red-950/30 border border-red-500/40 rounded-xl text-xs text-red-300 mt-3 flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-red-200">Baseline Flaw Exposed: </strong>
                      {response.execution_details.baseline_vulnerability}
                    </div>
                  </div>
                )}
              </div>

              {/* Toggle to inspect hidden background SQL */}
              <button
                onClick={() => setShowTechDetails(!showTechDetails)}
                className="text-xs text-slate-400 hover:text-slate-200 bg-slate-950 hover:bg-slate-800 border border-slate-800 px-3 py-1.5 rounded-lg transition-all flex items-center gap-1.5 shrink-0"
              >
                {showTechDetails ? <EyeOff className="w-3.5 h-3.5 text-sky-400" /> : <Eye className="w-3.5 h-3.5 text-sky-400" />}
                <span>{showTechDetails ? "Hide SQL & Logic" : "Inspect SQL & Logic"}</span>
              </button>
            </div>

            {/* Collapsible Inspection Drawer (Under the Hood) */}
            {showTechDetails && (
              <div className="mt-6 pt-5 border-t border-slate-800 space-y-4 animate-in fade-in duration-200">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                  <Database className="w-3.5 h-3.5 text-sky-400" />
                  Background SQL Execution & Verification
                </div>

                <div className="bg-slate-950 rounded-xl p-4 border border-slate-800 font-mono text-xs text-sky-300 overflow-x-auto">
                  <pre>{response.execution_details?.sql}</pre>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                    <span className="text-slate-500 block">Execution Latency</span>
                    <span className="text-slate-200 font-semibold">{response.execution_details?.execution_time_ms} ms</span>
                  </div>
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                    <span className="text-slate-500 block">Classification Rule</span>
                    <span className="text-slate-200 font-semibold truncate block">{response.execution_details?.rule_applied}</span>
                  </div>
                  <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                    <span className="text-slate-500 block">Mode</span>
                    <span className={`font-semibold uppercase ${mode === 'guided' ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {response.execution_details?.mode}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Structured Data Table */}
          {response.data?.length > 0 && (
            <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
              <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                  <Database className="w-4 h-4 text-sky-400" />
                  Verified Database Records
                </h3>
                <span className="text-xs text-slate-500">
                  Showing top {response.data.length} results
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-300">
                  <thead className="bg-slate-950/70 text-xs uppercase font-medium text-slate-400 border-b border-slate-800">
                    <tr>
                      {response.columns?.map((col) => (
                        <th key={col} className="px-6 py-3.5 tracking-wider">
                          {col.replace(/_/g, ' ')}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                    {response.data.map((row, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                        {response.columns?.map((col) => {
                          const val = row[col];
                          const isCurrency = col.includes('amount') || col.includes('price') || col.includes('revenue') || col.includes('spent') || col.includes('profit') || col.includes('discount');
                          const isStatus = col === 'status';

                          return (
                            <td key={col} className="px-6 py-3 whitespace-nowrap">
                              {isStatus ? (
                                <span className={`px-2 py-0.5 rounded-md text-[11px] font-sans font-semibold uppercase tracking-wider ${
                                  val === 'completed' || val === 'active' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                  val === 'returned' || val === 'pending' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                                  'bg-red-500/10 text-red-400 border border-red-500/20'
                                }`}>
                                  {val}
                                </span>
                              ) : isCurrency && typeof val === 'number' ? (
                                <span className="text-emerald-400 font-semibold font-mono">
                                  ${val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </span>
                              ) : (
                                <span className="font-sans text-slate-200">
                                  {val !== null && val !== undefined ? String(val) : '-'}
                                </span>
                              )}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
}
