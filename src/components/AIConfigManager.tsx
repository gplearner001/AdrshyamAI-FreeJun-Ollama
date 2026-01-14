import React, { useState, useEffect } from 'react';
import { Settings, Brain, Save, CheckCircle, XCircle, Loader2, RefreshCw } from 'lucide-react';
import { apiService } from '../services/api';
import { AIConfigResponse, AIConfigUpdateRequest, AIStatusResponse } from '../types';

export function AIConfigManager() {
  // State for the *saved* configuration (from /api/ai/config)
  const [selectedLlmService, setSelectedLlmService] = useState<'ollama' | 'claude'>('ollama');
  const [ollamaModelOverride, setOllamaModelOverride] = useState<string>('');
  const [claudeModelOverride, setClaudeModelOverride] = useState<string>('');

  // State for *status/environment* information (from /api/ai/status)
  const [ollamaApiUrlDisplay, setOllamaApiUrlDisplay] = useState<string>('');
  const [ollamaDefaultModel, setOllamaDefaultModel] = useState<string>('');
  const [ollamaAvailable, setOllamaAvailable] = useState<boolean>(false);

  const [claudeDefaultModel, setClaudeDefaultModel] = useState<string>('');
  const [claudeAvailable, setClaudeAvailable] = useState<boolean>(false);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<'ollama' | 'claude' | null>(null);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    fetchCombinedConfig();
  }, []);

  const fetchCombinedConfig = async () => {
    try {
      setLoading(true);
      // Fetch saved configuration
      const configResponse = await apiService.getAIConfig();
      if (configResponse.success) {
        setSelectedLlmService(configResponse.data.selected_llm_service);
        setOllamaModelOverride(configResponse.data.ollama_model || '');
        setClaudeModelOverride(configResponse.data.claude_model || '');
      } else {
        showMessage('error', configResponse.message || 'Failed to load saved AI configuration');
      }

      // Fetch AI service status (environment defaults, availability)
      const statusResponse = await apiService.getAIStatus();
      if (statusResponse.success) {
        setOllamaApiUrlDisplay(statusResponse.data.ollama_api_url || 'https://ollama.com');
        setOllamaDefaultModel(statusResponse.data.ollama_model || 'gpt-oss:120b-cloud');
        setOllamaAvailable(statusResponse.data.ollama_available);

        setClaudeDefaultModel(statusResponse.data.claude_model || 'Not set');
        setClaudeAvailable(statusResponse.data.claude_available);
      } else {
        showMessage('error', statusResponse.message || 'Failed to load AI service status');
      }

    } catch (error: any) {
      console.error('Error fetching AI config:', error);
      showMessage('error', `Failed to load configuration: ${error.message || error}`);
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async (service: 'ollama' | 'claude') => {
    setTesting(service);
    try {
      const response = await apiService.testAIConnection(service);

      if (response.success) {
        showMessage('success', `${service === 'ollama' ? 'Ollama' : 'Claude'} connection successful!`);
        // Re-fetch status to update availability indicator
        await fetchCombinedConfig();
      } else {
        showMessage('error', response.message || 'Connection test failed');
      }
    } catch (error: any) {
      console.error(`Error testing ${service}:`, error);
      showMessage('error', `Failed to test ${service} connection: ${error.message || error}`);
    } finally {
      setTesting(null);
    }
  };

  const saveConfig = async () => {
    try {
      setSaving(true);

      const payload: AIConfigUpdateRequest = {
        selected_llm_service: selectedLlmService,
        ollama_model: ollamaModelOverride || undefined, // Send undefined if empty string
        claude_model: claudeModelOverride || undefined, // Send undefined if empty string
      };

      const response = await apiService.updateAIConfig(payload);

      if (response.success) {
        showMessage('success', 'Configuration saved successfully');
        await fetchCombinedConfig(); // Re-fetch to ensure UI reflects saved state
      } else {
        showMessage('error', response.message || 'Failed to save configuration');
      }
    } catch (error: any) {
      console.error('Error saving config:', error);
      showMessage('error', `Failed to save configuration: ${error.message || error}`);
    } finally {
      setSaving(false);
    }
  };

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 overflow-hidden">
      <div
        className="p-6 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-r from-orange-500 to-red-600 p-3 rounded-lg">
              <Settings className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-800">AI Service Configuration</h2>
              <p className="text-sm text-gray-600">
                Active: <span className="font-semibold">{selectedLlmService === 'ollama' ? 'Ollama' : 'Claude'}</span>
                {selectedLlmService === 'ollama' ? (
                  <span className={`ml-2 ${ollamaAvailable ? 'text-green-600' : 'text-red-600'}`}>
                    ({ollamaAvailable ? 'Connected' : 'Disconnected'})
                  </span>
                ) : (
                  <span className={`ml-2 ${claudeAvailable ? 'text-green-600' : 'text-red-600'}`}>
                    ({claudeAvailable ? 'Connected' : 'Disconnected'})
                  </span>
                )}
              </p>
            </div>
          </div>
          <button className="text-gray-400 hover:text-gray-600">
            <Settings className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="p-6 border-t border-gray-200 bg-gray-50">
          {message && (
            <div className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${
              message.type === 'success'
                ? 'bg-green-50 text-green-800 border border-green-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}>
              {message.type === 'success' ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <XCircle className="w-5 h-5" />
              )}
              <span className="text-sm font-medium">{message.text}</span>
            </div>
          )}

          {loading ? (
            <div className="text-center py-8">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2 text-gray-400" />
              <p className="text-gray-600">Loading configuration...</p>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="bg-white rounded-lg p-6 border border-gray-200">
                <h3 className="text-lg font-semibold mb-4">Active AI Service</h3>
                <div className="grid grid-cols-2 gap-4">
                  <button
                    onClick={() => setSelectedLlmService('ollama')}
                    className={`p-4 border-2 rounded-lg transition-all ${
                      selectedLlmService === 'ollama'
                        ? 'border-orange-500 bg-orange-50'
                        : 'border-gray-200 hover:border-orange-300'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <Brain className={`w-6 h-6 ${selectedLlmService === 'ollama' ? 'text-orange-600' : 'text-gray-400'}`} />
                      <span className="font-semibold">Ollama</span>
                    </div>
                    {ollamaAvailable && (
                      <span className="text-xs text-green-600">Available</span>
                    )}
                  </button>

                  <button
                    onClick={() => setSelectedLlmService('claude')}
                    className={`p-4 border-2 rounded-lg transition-all ${
                      selectedLlmService === 'claude'
                        ? 'border-orange-500 bg-orange-50'
                        : 'border-gray-200 hover:border-orange-300'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2 mb-2">
                          <Brain className={`w-6 h-6 ${selectedLlmService === 'claude' ? 'text-orange-600' : 'text-gray-400'}`} />
                      <span className="font-semibold">Claude</span>
                    </div>
                    {claudeAvailable && (
                      <span className="text-xs text-green-600">Available</span>
                    )}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-lg p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Brain className="w-5 h-5 text-orange-600" />
                    Ollama Configuration
                  </h3>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        API URL (from .env)
                      </label>
                      <input
                        type="text"
                        value={ollamaApiUrlDisplay}
                        readOnly
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600 cursor-not-allowed"
                      />
                      <p className="text-xs text-gray-500 mt-1">Set `OLLAMA_API_URL` in your backend's .env file.</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Default Model (from .env)
                      </label>
                      <input
                        type="text"
                        value={ollamaDefaultModel}
                        readOnly
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600 cursor-not-allowed"
                      />
                      <p className="text-xs text-gray-500 mt-1">Set `OLLAMA_MODEL` in your backend's .env file.</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Override Model (Optional)
                      </label>
                      <input
                        type="text"
                        value={ollamaModelOverride}
                        onChange={(e) => setOllamaModelOverride(e.target.value)}
                        placeholder={ollamaDefaultModel || "e.g., llama3.2"}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      />
                      <p className="text-xs text-gray-500 mt-1">Leave blank to use default from .env.</p>
                    </div>

                    <button
                      onClick={() => testConnection('ollama')}
                      disabled={testing === 'ollama'}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:bg-gray-400"
                    >
                      {testing === 'ollama' ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4" />
                      )}
                      Test Connection
                    </button>
                  </div>
                </div>

                <div className="bg-white rounded-lg p-6 border border-gray-200">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Brain className="w-5 h-5 text-orange-600" />
                    Claude Configuration
                  </h3>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        API Key (from .env)
                      </label>
                      <input
                        type="password"
                        value="********************" // Always mask API key for display
                        readOnly
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600 cursor-not-allowed"
                      />
                      <p className="text-xs text-gray-500 mt-1">Set `CLAUDE_API_KEY` in your backend's .env file.</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Default Model (from .env)
                      </label>
                      <input
                        type="text"
                        value={claudeDefaultModel}
                        readOnly
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-600 cursor-not-allowed"
                      />
                      <p className="text-xs text-gray-500 mt-1">Set `CLAUDE_MODEL` in your backend's .env file.</p>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Override Model (Optional)
                      </label>
                      <select
                        value={claudeModelOverride}
                        onChange={(e) => setClaudeModelOverride(e.target.value)}
                        className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-orange-500 focus:border-transparent"
                      >
                        <option value="">Use Default ({claudeDefaultModel || 'Not set'})</option>
                        <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
                        <option value="claude-3-opus-20240229">Claude 3 Opus</option>
                        <option value="claude-3-sonnet-20240229">Claude 3 Sonnet</option>
                        <option value="claude-3-haiku-20240307">Claude 3 Haiku</option>
                      </select>
                      <p className="text-xs text-gray-500 mt-1">Leave blank to use default from .env.</p>
                    </div>

                    <button
                      onClick={() => testConnection('claude')}
                      disabled={testing === 'claude'}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:bg-gray-400"
                    >
                      {testing === 'claude' ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4" />
                      )}
                      Test Connection
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-4 pt-4 border-t border-gray-200">
                <button
                  onClick={fetchCombinedConfig}
                  disabled={loading || saving}
                  className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors disabled:bg-gray-100"
                >
                  Reset
                </button>
                <button
                  onClick={saveConfig}
                  disabled={saving}
                  className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-orange-600 to-red-600 text-white rounded-lg hover:from-orange-700 hover:to-red-700 transition-colors disabled:opacity-50"
                >
                  {saving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Save className="w-4 h-4" />
                  )}
                  Save Configuration
                </button>
              </div>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <h4 className="text-sm font-semibold text-blue-800 mb-2">Configuration Notes:</h4>
                <ul className="text-xs text-blue-700 space-y-1">
                  <li>Ollama runs locally and requires installation on your machine.</li>
                  <li>Claude requires an API key from Anthropic.</li>
                  <li>API URLs and Keys are read from backend environment variables (.env file).</li>
                  <li>Override models are saved to the database and take precedence over .env defaults.</li>
                  <li>Test connections before saving to ensure proper configuration.</li>
                  <li>Active service will be used for all AI-powered conversations.</li>
                  <li>Configuration changes take effect immediately after saving.</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
