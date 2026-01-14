import React, { useState, useEffect } from 'react';
import { Brain, BrainCircuit, AlertTriangle } from 'lucide-react';
import { apiService } from '../services/api';

export const AIStatusIndicator: React.FC = () => {
  const [aiStatus, setAiStatus] = useState<{
    ollama_available: boolean;
    claude_available?: boolean;
    active_service?: string;
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
    const interval = setInterval(checkAIStatus, 60000);

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

  const isAvailable = aiStatus.active_service === 'ollama'
    ? aiStatus.ollama_available
    : aiStatus.claude_available;

  const serviceName = aiStatus.active_service === 'ollama' ? 'Ollama' : 'Claude';

  return (
    <div className={`flex items-center gap-2 ${
      isAvailable ? 'text-green-600' : 'text-orange-500'
    }`}>
      {isAvailable ? (
        <BrainCircuit className="w-4 h-4" />
      ) : (
        <Brain className="w-4 h-4" />
      )}
      <span className="text-sm">
        {serviceName} {isAvailable ? 'Active' : 'Inactive'}
        {aiStatus.model && <span className="text-xs ml-1">({aiStatus.model})</span>}
      </span>
    </div>
  );
};
