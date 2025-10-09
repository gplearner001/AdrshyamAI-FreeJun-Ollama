import React, { useState, useEffect } from 'react';
import { Brain, BrainCircuit, AlertTriangle } from 'lucide-react';
import { apiService } from '../services/api';

export const AIStatusIndicator: React.FC = () => {
  const [aiStatus, setAiStatus] = useState<{
    ollama_available: boolean;
    service: string;
    model: string | null;
    api_url?: string;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAIStatus = async () => {
      try {
        const response = await apiService.getAIStatus();
        setAiStatus(response.data);
      } catch (error) {
        console.error('Failed to check AI status:', error);
        setAiStatus(null);
      } finally {
        setIsLoading(false);
      }
    };

    checkAIStatus();
    const interval = setInterval(checkAIStatus, 60000); // Check every minute

    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-gray-500">
        <AlertTriangle className="w-4 h-4" />
        <span className="text-sm">Checking AI status...</span>
      </div>
    );
  }

  if (!aiStatus) {
    return (
      <div className="flex items-center gap-2 text-red-600">
        <Brain className="w-4 h-4" />
        <span className="text-sm">AI Service Offline</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${
      aiStatus.ollama_available ? 'text-green-600' : 'text-gray-500'
    }`}>
      {aiStatus.ollama_available ? (
        <BrainCircuit className="w-4 h-4" />
      ) : (
        <Brain className="w-4 h-4" />
      )}
      <span className="text-sm">
        {aiStatus.ollama_available
          ? `Ollama LLM Active (${aiStatus.model || 'llama3.2'})`
          : 'AI Service Unavailable'
        }
      </span>
    </div>
  );
};