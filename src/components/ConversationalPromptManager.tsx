import React, { useState, useEffect } from 'react';
import { MessageSquare, Save, Plus, Trash2, Edit2, CheckCircle, XCircle, Loader2 } from 'lucide-react';

interface ConversationalPrompt {
  id: string;
  name: string;
  system_prompt: string;
  greeting_message?: string;
  user_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function ConversationalPromptManager() {
  const [prompts, setPrompts] = useState<ConversationalPrompt[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<ConversationalPrompt | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState<string>('');
  const [promptName, setPromptName] = useState('');
  const [greetingMessage, setGreetingMessage] = useState('');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const userId = 'demo-user-123';

  useEffect(() => {
    fetchPrompts();
  }, []);

  const fetchPrompts = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE_URL}/api/prompts?user_id=${userId}`, {
        headers: { 'ngrok-skip-browser-warning': 'true' }
      });
      const data = await response.json();
      if (data.success) {
        setPrompts(data.data);
        const activePrompt = data.data.find((p: ConversationalPrompt) => p.is_active);
        if (activePrompt) {
          setSelectedPrompt(activePrompt);
          setEditingPrompt(activePrompt.system_prompt);
          setPromptName(activePrompt.name);
          setGreetingMessage(activePrompt.greeting_message || '');
        }
      }
    } catch (error) {
      console.error('Error fetching prompts:', error);
      showMessage('error', 'Failed to load prompts');
    } finally {
      setLoading(false);
    }
  };

  const createPrompt = async () => {
    if (!promptName.trim() || !editingPrompt.trim()) {
      showMessage('error', 'Name and prompt text are required');
      return;
    }

    try {
      setSaving(true);
      const response = await fetch(`${API_BASE_URL}/api/prompts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({
          name: promptName,
          system_prompt: editingPrompt,
          greeting_message: greetingMessage,
          user_id: userId,
          is_active: false
        })
      });

      const data = await response.json();
      if (data.success) {
        showMessage('success', 'Prompt created successfully');
        setShowCreateForm(false);
        setPromptName('');
        setEditingPrompt('');
        setGreetingMessage('');
        await fetchPrompts();
      } else {
        showMessage('error', data.error || 'Failed to create prompt');
      }
    } catch (error) {
      console.error('Error creating prompt:', error);
      showMessage('error', 'Failed to create prompt');
    } finally {
      setSaving(false);
    }
  };

  const updatePrompt = async () => {
    if (!selectedPrompt || !editingPrompt.trim()) {
      showMessage('error', 'Prompt text is required');
      return;
    }

    try {
      setSaving(true);
      const response = await fetch(`${API_BASE_URL}/api/prompts/${selectedPrompt.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({
          name: promptName,
          system_prompt: editingPrompt,
          greeting_message: greetingMessage
        })
      });

      const data = await response.json();
      if (data.success) {
        showMessage('success', 'Prompt updated successfully');
        await fetchPrompts();
      } else {
        showMessage('error', data.error || 'Failed to update prompt');
      }
    } catch (error) {
      console.error('Error updating prompt:', error);
      showMessage('error', 'Failed to update prompt');
    } finally {
      setSaving(false);
    }
  };

  const setActivePrompt = async (promptId: string) => {
    try {
      setSaving(true);
      const response = await fetch(`${API_BASE_URL}/api/prompts/${promptId}/activate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        }
      });

      const data = await response.json();
      if (data.success) {
        showMessage('success', 'Active prompt updated');
        await fetchPrompts();
      } else {
        showMessage('error', data.error || 'Failed to activate prompt');
      }
    } catch (error) {
      console.error('Error activating prompt:', error);
      showMessage('error', 'Failed to activate prompt');
    } finally {
      setSaving(false);
    }
  };

  const deletePrompt = async (promptId: string) => {
    if (!confirm('Are you sure you want to delete this prompt?')) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/prompts/${promptId}`, {
        method: 'DELETE',
        headers: { 'ngrok-skip-browser-warning': 'true' }
      });

      const data = await response.json();
      if (data.success) {
        showMessage('success', 'Prompt deleted successfully');
        if (selectedPrompt?.id === promptId) {
          setSelectedPrompt(null);
          setEditingPrompt('');
          setPromptName('');
          setGreetingMessage('');
        }
        await fetchPrompts();
      } else {
        showMessage('error', data.error || 'Failed to delete prompt');
      }
    } catch (error) {
      console.error('Error deleting prompt:', error);
      showMessage('error', 'Failed to delete prompt');
    }
  };

  const selectPrompt = (prompt: ConversationalPrompt) => {
    setSelectedPrompt(prompt);
    setEditingPrompt(prompt.system_prompt);
    setPromptName(prompt.name);
    setGreetingMessage(prompt.greeting_message || '');
    setShowCreateForm(false);
  };

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const resetForm = () => {
    setShowCreateForm(false);
    setPromptName('');
    setEditingPrompt('');
    setGreetingMessage('');
    if (selectedPrompt) {
      setEditingPrompt(selectedPrompt.system_prompt);
      setPromptName(selectedPrompt.name);
      setGreetingMessage(selectedPrompt.greeting_message || '');
    }
  };

  const defaultPromptTemplate = `You are an AI assistant in a voice call conversation.

IMPORTANT CONVERSATION RULES:
1. Keep responses SHORT (1-2 sentences maximum)
2. Respond naturally and conversationally
3. DO NOT ask multiple questions in one response
4. Wait for the user to speak - don't dominate the conversation
5. Be helpful but concise
6. If user says something brief or unclear, ask ONE clarifying question
7. Don't repeat the same type of response multiple times

Provide a SHORT, helpful response that continues the conversation naturally.
Remember: This is a voice call - keep it brief and conversational!`;

  return (
    <div className="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="bg-gradient-to-r from-blue-500 to-purple-600 p-3 rounded-lg">
            <MessageSquare className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-800">Conversational Prompt Manager</h2>
            <p className="text-sm text-gray-600">Configure AI behavior for voice conversations</p>
          </div>
        </div>
        <button
          onClick={() => {
            setShowCreateForm(true);
            setSelectedPrompt(null);
            setEditingPrompt(defaultPromptTemplate);
            setPromptName('');
            setGreetingMessage('');
          }}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Prompt
        </button>
      </div>

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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <h3 className="text-lg font-semibold mb-3">Saved Prompts</h3>
          {loading ? (
            <div className="text-center py-8 text-gray-500">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
              Loading...
            </div>
          ) : prompts.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <MessageSquare className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p>No prompts yet</p>
              <p className="text-sm text-gray-400 mt-1">Create your first prompt</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {prompts.map((prompt) => (
                <div
                  key={prompt.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-all ${
                    selectedPrompt?.id === prompt.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-blue-300'
                  } ${prompt.is_active ? 'ring-2 ring-green-500' : ''}`}
                  onClick={() => selectPrompt(prompt)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-semibold text-gray-900">{prompt.name}</h4>
                        {prompt.is_active && (
                          <span className="px-2 py-0.5 text-xs bg-green-100 text-green-700 rounded-full">
                            Active
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {prompt.system_prompt.substring(0, 60)}...
                      </p>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deletePrompt(prompt.id);
                      }}
                      className="text-red-500 hover:text-red-700 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold">
              {showCreateForm ? 'Create New Prompt' : selectedPrompt ? 'Edit Prompt' : 'Prompt Editor'}
            </h3>
            {!showCreateForm && selectedPrompt && !selectedPrompt.is_active && (
              <button
                onClick={() => setActivePrompt(selectedPrompt.id)}
                disabled={saving}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:bg-gray-400"
              >
                <CheckCircle className="w-4 h-4" />
                Set as Active
              </button>
            )}
          </div>

          {!showCreateForm && !selectedPrompt ? (
            <div className="text-center py-12 text-gray-500">
              <Edit2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p>Select a prompt to edit or create a new one</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Prompt Name
                </label>
                <input
                  type="text"
                  value={promptName}
                  onChange={(e) => setPromptName(e.target.value)}
                  placeholder="e.g., Customer Support Assistant"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Greeting Message (optional)
                </label>
                <input
                  type="text"
                  value={greetingMessage}
                  onChange={(e) => setGreetingMessage(e.target.value)}
                  placeholder="e.g., Hello! How can I help you today?"
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <p className="text-xs text-gray-500 mt-1">
                  The first message the AI sends to start the conversation.
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  System Prompt
                </label>
                <textarea
                  value={editingPrompt}
                  onChange={(e) => setEditingPrompt(e.target.value)}
                  placeholder="Enter your conversational prompt here..."
                  rows={12}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Characters: {editingPrompt.length} | Lines: {editingPrompt.split('\n').length}
                </p>
              </div>

              <div className="flex gap-3">
                {showCreateForm ? (
                  <>
                    <button
                      onClick={createPrompt}
                      disabled={saving || !promptName.trim() || !editingPrompt.trim()}
                      className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
                    >
                      {saving ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Plus className="w-4 h-4" />
                      )}
                      Create Prompt
                    </button>
                    <button
                      onClick={resetForm}
                      disabled={saving}
                      className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={updatePrompt}
                      disabled={saving || !editingPrompt.trim()}
                      className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
                    >
                      {saving ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Save className="w-4 h-4" />
                      )}
                      Save Changes
                    </button>
                    <button
                      onClick={resetForm}
                      disabled={saving}
                      className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
                    >
                      Reset
                    </button>
                  </>
                )}
              </div>
            </div>
          )}

          <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <h4 className="text-sm font-semibold text-blue-800 mb-2">Tips for effective prompts:</h4>
            <ul className="text-xs text-blue-700 space-y-1">
              <li>Keep instructions clear and concise</li>
              <li>Define the AI's role and personality</li>
              <li>Specify response length and format preferences</li>
              <li>Include conversation guidelines (e.g., tone, politeness)</li>
              <li>Add any domain-specific knowledge or constraints</li>
              <li>Test your prompts to ensure desired behavior</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
