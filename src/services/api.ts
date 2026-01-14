import { CallRequest, CallResponse, CallHistoryItem, ApiResponse, AIConfigResponse, AIConfigUpdateRequest, AIStatusResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiService {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true',
          ...options?.headers,
        },
        ...options,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  async initiateCall(callRequest: CallRequest): Promise<ApiResponse<CallResponse>> {
    return this.request<CallResponse>('/api/calls/initiate', {
      method: 'POST',
      body: JSON.stringify(callRequest),
    });
  }

  async getCallHistory(): Promise<ApiResponse<CallHistoryItem[]>> {
    return this.request<CallHistoryItem[]>('/api/calls/history');
  }

  async getActiveCalls(): Promise<ApiResponse<any[]>> {
    return this.request<any[]>('/api/calls/active');
  }

  async getCallDetails(callId: string): Promise<ApiResponse<CallResponse>> {
    return this.request<CallResponse>(`/api/calls/${callId}`);
  }

  async checkHealth(): Promise<ApiResponse<{ status: string; message: string }>> {
    return this.request<{ status: string; message: string }>('/health');
  }

  async generateAIResponse(conversationData: {
    history: Array<{ role: string; content: string }>;
    current_input: string;
    call_id?: string;
    context?: any;
    knowledge_base_id?: string;
  }): Promise<ApiResponse<{ response: string; timestamp: string }>> {
    return this.request<{ response: string; timestamp: string }>('/api/ai/conversation', {
      method: 'POST',
      body: JSON.stringify(conversationData),
    });
  }

  async getAIStatus(): Promise<ApiResponse<AIStatusResponse>> {
    return this.request<AIStatusResponse>('/api/ai/status');
  }

  async getAIConfig(): Promise<ApiResponse<AIConfigResponse>> {
    return this.request<AIConfigResponse>('/api/ai/config');
  }

  async updateAIConfig(config: AIConfigUpdateRequest): Promise<ApiResponse<AIConfigResponse>> {
    return this.request<AIConfigResponse>('/api/ai/config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  }

  async testAIConnection(service: 'ollama' | 'claude'): Promise<ApiResponse<any>> {
    // Backend test endpoints are GET and rely on environment variables
    return this.request<any>(`/api/ai/test/${service}`);
  }
}

export const apiService = new ApiService();
