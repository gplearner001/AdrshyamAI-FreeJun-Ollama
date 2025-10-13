import React, { useState } from 'react';
import { MessageSquare, Send, Loader2, Brain } from 'lucide-react';
import { apiService } from '../services/api';
import { KnowledgeBaseSelector } from './KnowledgeBaseSelector';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface AIConversationPanelProps {
  selectedKnowledgeBaseId: string;
  onKnowledgeBaseChange: (kbId: string) => void;
}

export const AIConversationPanel: React.FC<AIConversationPanelProps> = ({
  selectedKnowledgeBaseId,
  onKnowledgeBaseChange
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async () => {
    if (!inputText.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: inputText,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const requestData: any = {
        history: messages.map(msg => ({ role: msg.role, content: msg.content })),
        current_input: inputText,
        context: { source: 'conversation_panel' }
      };

      if (selectedKnowledgeBaseId && selectedKnowledgeBaseId.trim() !== '') {
        requestData.knowledge_base_id = selectedKnowledgeBaseId;
      }

      const response = await apiService.generateAIResponse(requestData);

      const aiMessage: Message = {
        role: 'assistant',
        content: response.data.response,
        timestamp: response.data.timestamp
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Failed to get AI response:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'I apologize, but I\'m having trouble processing your request right now.',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 h-96 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-3 mb-3">
          <div className="bg-gradient-to-r from-green-500 to-emerald-600 p-2 rounded-lg">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <h3 className="text-lg font-semibold text-gray-800">AI Conversation</h3>
          <span className="text-sm text-gray-500">Powered by AdrshyamAI</span>
        </div>

        <KnowledgeBaseSelector
          selectedKbId={selectedKnowledgeBaseId}
          onSelectKb={onKnowledgeBaseChange}
          label="Knowledge Base (optional)"
          showActiveIndicator={true}
        />
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>Start a conversation with AdrshyamAI</p>
            <p className="text-sm text-gray-400 mt-1">
              {selectedKnowledgeBaseId
                ? 'Ask questions based on your knowledge base documents'
                : 'Ask questions about call flows, voice interactions, or anything else!'}
            </p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                <p className="text-sm">{message.content}</p>
                <p className={`text-xs mt-1 ${
                  message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                }`}>
                  {new Date(message.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 px-4 py-2 rounded-lg flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Ollama is thinking...</span>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 border-t border-gray-200">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask Ollama anything..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent text-sm"
            disabled={isLoading}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputText.trim() || isLoading}
            className="bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white px-4 py-2 rounded-lg transition-all duration-200 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};