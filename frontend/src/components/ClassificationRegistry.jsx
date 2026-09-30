import React, { useState, useEffect } from 'react';
import { BookOpen, RefreshCw, ShieldCheck, Tag, Code, CheckCircle2, ChevronRight, HelpCircle } from 'lucide-react';

export default function ClassificationRegistry({ onSelectQuery }) {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('all');

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/classification-rules');
      const data = await res.json();
      setRules(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const categories = [
    { id: 'all', label: 'All Rules' },
    { id: 'superlative', label: 'Superlatives' },
    { id: 'temporal', label: 'Temporal Boundaries' },
    { id: 'lifecycle', label: 'Customer Lifecycle' },
    { id: 'financial', label: 'Financial Semantics' }
  ];

  const filteredRules = rules.filter(r => activeTab === 'all' || r.category === activeTab);

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
                Single Source of Truth
              </span>
              <span className="text-xs text-slate-400">Database Table: metric_classification_rules</span>
            </div>
            <h2 className="text-2xl font-bold text-white mt-1">
              Enterprise Business Classification Registry
            </h2>
            <p className="text-sm text-slate-400 mt-1 max-w-3xl">
              Certified semantic business definitions that resolve natural language ambiguities before queries hit the database.
              Guarantees GAAP revenue standards, prevents silent data corruption, and enforces status filtering.
            </p>
          </div>

          <button
            onClick={fetchRules}
            disabled={loading}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3.5 py-2 rounded-xl transition-all border border-slate-700 flex items-center gap-1.5 self-start shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Reload Rules</span>
          </button>
        </div>

        {/* Categories Bar */}
        <div className="flex flex-wrap gap-2 mt-6 pt-5 border-t border-slate-800">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveTab(cat.id)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === cat.id
                  ? 'bg-sky-500 text-white shadow-md shadow-sky-500/20'
                  : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {filteredRules.map((rule) => (
          <div
            key={rule.rule_id}
            className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg flex flex-col justify-between hover:border-slate-700 transition-all space-y-4"
          >
            <div>
              <div className="flex items-center justify-between gap-2 mb-2">
                <span className="text-xs font-mono font-bold text-sky-400 bg-sky-950/70 border border-sky-800/40 px-2 py-0.5 rounded">
                  @{rule.term_alias}
                </span>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-800 px-2 py-0.5 rounded">
                  {rule.category}
                </span>
              </div>

              <h3 className="text-base font-bold text-white mb-1">{rule.title}</h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-3">{rule.description}</p>

              {/* Primary Metric Definition */}
              <div className="bg-slate-950 p-3 rounded-xl border border-slate-800/80 space-y-2 text-xs">
                <div>
                  <span className="text-slate-500 font-medium block">Certified Primary Metric:</span>
                  <span className="text-emerald-400 font-semibold">{rule.primary_metric}</span>
                </div>
                <div>
                  <span className="text-slate-500 font-medium block">SQL Standard Formula:</span>
                  <code className="text-sky-300 font-mono text-[11px] block bg-slate-900 p-1.5 rounded mt-0.5 overflow-x-auto">
                    {rule.primary_sql_expression}
                  </code>
                </div>
                <div>
                  <span className="text-slate-500 font-medium block">Required Filter Guardrails:</span>
                  <code className="text-amber-300 font-mono text-[11px] block bg-slate-900 p-1.5 rounded mt-0.5 overflow-x-auto">
                    {rule.filter_conditions}
                  </code>
                </div>
              </div>

              {/* Alternatives List */}
              {rule.alternative_metrics?.length > 0 && (
                <div className="mt-3">
                  <span className="text-[11px] font-semibold text-slate-400 block mb-1.5">
                    Selectable Business Alternatives:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {rule.alternative_metrics.map((alt, i) => (
                      <span
                        key={i}
                        className="text-[10px] bg-slate-800/80 text-slate-300 border border-slate-700/60 px-2 py-1 rounded"
                      >
                        {alt.label}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Rationale & Baseline Failure Note */}
              <div className="mt-3 pt-3 border-t border-slate-800 space-y-2 text-xs">
                <div className="text-slate-300">
                  <strong className="text-slate-200">Accounting Rationale: </strong>
                  <span className="text-slate-400">{rule.rationale}</span>
                </div>
                <div className="p-2.5 bg-red-950/20 border border-red-500/30 rounded-lg text-red-300 text-[11px]">
                  <strong>Baseline Flaw Without Rule: </strong>
                  <span className="text-red-200/90">{rule.why_baseline_fails}</span>
                </div>
              </div>
            </div>

            {/* Test Button */}
            <button
              onClick={() => onSelectQuery && onSelectQuery(`Show me ${rule.title.toLowerCase()}`)}
              className="w-full text-xs font-semibold bg-slate-800 hover:bg-sky-600 hover:text-white text-slate-300 py-2 rounded-xl transition-all flex items-center justify-center gap-1.5 border border-slate-700"
            >
              <span>Test This Rule in Assistant</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
