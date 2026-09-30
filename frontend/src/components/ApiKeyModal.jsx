import React, { useState, useEffect } from 'react';
import { 
  Key, Shield, CheckCircle2, AlertTriangle, ExternalLink, 
  X, RefreshCw, Cpu, Zap, FileText, Check, Copy
} from 'lucide-react';

export default function ApiKeyModal({ isOpen, onClose, config, onConfigSaved }) {
  if (!isOpen) return null;

  const [geminiKey, setGeminiKey] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [openaiBaseUrl, setOpenaiBaseUrl] = useState(config?.openai_base_url || 'https://api.openai.com/v1');
  const [provider, setProvider] = useState(config?.active_provider || 'auto');
  const [saving, setSaving] = useState(false);
  const [testStatus, setTestStatus] = useState(null); // { provider, testing, success, message }
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (config) {
      setProvider(config.active_provider || 'auto');
      setOpenaiBaseUrl(config.openai_base_url || 'https://api.openai.com/v1');
    }
  }, [config]);

  const handleTestKey = async (targetProvider) => {
    const key = targetProvider === 'gemini' ? geminiKey : openaiKey;
    if (!key.trim()) {
      setTestStatus({
        provider: targetProvider,
        testing: false,
        success: false,
        message: `Please paste your ${targetProvider === 'gemini' ? 'Google Gemini' : 'OpenAI'} API key above first.`
      });
      return;
    }

    setTestStatus({ provider: targetProvider, testing: true, success: null, message: 'Validating API key...' });
    try {
      const res = await fetch('/api/test-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: targetProvider,
          api_key: key.trim(),
          base_url: targetProvider === 'openai' ? openaiBaseUrl.trim() : undefined
        })
      });
      const data = await res.json();
      setTestStatus({
        provider: targetProvider,
        testing: false,
        success: data.success,
        message: data.message
      });
    } catch (err) {
      setTestStatus({
        provider: targetProvider,
        testing: false,
        success: false,
        message: `Network error reaching backend: ${err.message}`
      });
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveSuccess(false);

    try {
      const payload = {
        llm_provider: provider
      };
      if (geminiKey.trim()) {
        payload.gemini_api_key = geminiKey.trim();
      }
      if (openaiKey.trim()) {
        payload.openai_api_key = openaiKey.trim();
      }
      if (openaiBaseUrl.trim()) {
        payload.openai_base_url = openaiBaseUrl.trim();
      }

      const res = await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        setSaveSuccess(true);
        if (onConfigSaved) onConfigSaved();
        setTimeout(() => {
          setSaveSuccess(false);
          onClose();
        }, 1200);
      } else {
        alert(data.detail || 'Failed to save configuration.');
      }
    } catch (err) {
      alert(`Error saving configuration: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-sky-500/10 rounded-xl text-sky-400">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-base text-white">LLM Provider & API Key Settings</h3>
              <p className="text-xs text-slate-400">Configure your LLM model or use the built-in offline engine</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <form onSubmit={handleSave} className="p-6 overflow-y-auto space-y-5 flex-1">
          {/* Active Engine Card */}
          <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
                <Cpu className="w-4 h-4" />
              </div>
              <div>
                <div className="text-xs text-slate-400">Currently Active Engine</div>
                <div className="text-sm font-semibold text-white">
                  {config?.active_model_desc || 'Built-in Semantic Engine (Offline)'}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Operational</span>
            </div>
          </div>

          {/* Provider Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-2">
              Select SQL Generation Provider
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {[
                {
                  id: 'auto',
                  title: 'Auto (Recommended)',
                  desc: 'Uses Gemini/OpenAI if key exists, else offline engine',
                  icon: Zap
                },
                {
                  id: 'semantic_engine',
                  title: 'Built-in Semantic Engine',
                  desc: '100% offline, zero setup, 0 API keys required',
                  icon: Cpu
                },
                {
                  id: 'gemini',
                  title: 'Google Gemini',
                  desc: 'Direct calls to gemini-1.5-flash',
                  icon: Key
                },
                {
                  id: 'openai',
                  title: 'OpenAI',
                  desc: 'Direct calls to gpt-4o-mini',
                  icon: Key
                }
              ].map((item) => {
                const Icon = item.icon;
                const isSelected = provider === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setProvider(item.id)}
                    className={`p-3 rounded-xl border text-left transition-all flex items-start gap-2.5 ${
                      isSelected 
                        ? 'bg-sky-500/10 border-sky-500 text-white' 
                        : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <Icon className={`w-4 h-4 mt-0.5 ${isSelected ? 'text-sky-400' : 'text-slate-500'}`} />
                    <div>
                      <div className="text-xs font-semibold">{item.title}</div>
                      <div className="text-[11px] text-slate-400 leading-tight mt-0.5">{item.desc}</div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Google Gemini API Key Input */}
          <div className="space-y-1.5 pt-1">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <span>Google Gemini API Key</span>
                {config?.has_gemini_key && (
                  <span className="text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-1.5 py-0.2 rounded font-mono">
                    Key Set: {config.gemini_masked_key}
                  </span>
                )}
              </label>
              <a 
                href="https://aistudio.google.com/app/apikey" 
                target="_blank" 
                rel="noreferrer"
                className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1"
              >
                <span>Get Free Gemini Key</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder={config?.has_gemini_key ? "Paste new key to replace existing" : "AIzaSy..."}
                className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500 font-mono"
              />
              <button
                type="button"
                onClick={() => handleTestKey('gemini')}
                disabled={testStatus?.testing}
                className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl border border-slate-700 transition-all flex items-center gap-1.5"
              >
                {testStatus?.testing && testStatus?.provider === 'gemini' ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-sky-400" />
                ) : (
                  <span>Test Key</span>
                )}
              </button>
            </div>
          </div>

          {/* OpenAI Configuration Section (API Key + Base URL for AI Credits Platforms) */}
          <div className="space-y-3 pt-2 border-t border-slate-800/80">
            <div className="flex items-center justify-between">
              <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <span>OpenAI / AI Credits Platform Configuration</span>
                {config?.has_openai_key && (
                  <span className="text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-1.5 py-0.2 rounded font-mono">
                    Key Set: {config.openai_masked_key}
                  </span>
                )}
              </div>
              <a 
                href="https://platform.openai.com/api-keys" 
                target="_blank" 
                rel="noreferrer"
                className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1"
              >
                <span>Official OpenAI Docs</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            {/* Custom Base URL Input */}
            <div className="space-y-1 bg-slate-950/50 p-3 rounded-xl border border-slate-800">
              <div className="flex items-center justify-between">
                <label className="text-[11px] font-semibold text-slate-300">
                  OpenAI Base URL <span className="text-slate-500 font-normal">(AI Credits Platform / Relay / Reverse Proxy)</span>:
                </label>
                <button
                  type="button"
                  onClick={() => setOpenaiBaseUrl('https://api.openai.com/v1')}
                  className="text-[10px] text-sky-400 hover:text-sky-300 bg-slate-900 px-2 py-0.5 rounded border border-slate-800 transition-all"
                >
                  Reset Default
                </button>
              </div>
              <input
                type="text"
                value={openaiBaseUrl}
                onChange={(e) => setOpenaiBaseUrl(e.target.value)}
                placeholder="e.g. https://api.openai.com/v1 or https://your-ai-credits-platform.com/v1"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500 font-mono"
              />
              <p className="text-[10px] text-slate-500">
                If using an AI credits platform or custom proxy, paste its base URL above (e.g. <code className="text-sky-400">https://relay.aicredits.io/v1</code>).
              </p>
            </div>

            {/* OpenAI API Key Input */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-400">
                OpenAI / AI Credits API Key:
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="password"
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder={config?.has_openai_key ? "Paste new key to replace existing" : "sk-... or your credits platform key"}
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500 font-mono"
                />
                <button
                  type="button"
                  onClick={() => handleTestKey('openai')}
                  disabled={testStatus?.testing}
                  className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl border border-slate-700 transition-all flex items-center gap-1.5"
                >
                  {testStatus?.testing && testStatus?.provider === 'openai' ? (
                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-sky-400" />
                  ) : (
                    <span>Test Key</span>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Test Status Banner */}
          {testStatus && (
            <div className={`p-3 rounded-xl border text-xs flex items-start gap-2.5 ${
              testStatus.success === true
                ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                : testStatus.success === false
                ? 'bg-rose-950/40 border-rose-500/30 text-rose-300'
                : 'bg-sky-950/40 border-sky-500/30 text-sky-300'
            }`}>
              {testStatus.success === true ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
              ) : testStatus.success === false ? (
                <AlertTriangle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
              ) : (
                <RefreshCw className="w-4 h-4 text-sky-400 mt-0.5 shrink-0 animate-spin" />
              )}
              <div className="flex-1 font-mono text-[11px] leading-relaxed">
                {testStatus.message}
              </div>
            </div>
          )}

          {/* Config Files Information Box */}
          <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
            <div className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-sky-400" />
              <span>Configuration Files on Disk</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              When you click Save, your keys are automatically written to both <code className="text-sky-300 bg-slate-900 px-1 rounded">env.config</code> and <code className="text-sky-300 bg-slate-900 px-1 rounded">.env</code> in your project root. You can also edit <code className="text-sky-300 bg-slate-900 px-1 rounded">env.config</code> directly with any text editor.
            </p>
          </div>

          {/* Save Action Buttons */}
          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-sky-500/20 transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {saving ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : saveSuccess ? (
                <>
                  <Check className="w-3.5 h-3.5 text-white" />
                  <span>Saved!</span>
                </>
              ) : (
                <span>Save Configuration</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
