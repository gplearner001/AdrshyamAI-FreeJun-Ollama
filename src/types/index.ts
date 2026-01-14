export interface CallRequest {
  from_number: string;
  to_number: string;
  flow_url: string;
  status_callback_url?: string;
  knowledge_base_id?: string;
}

export interface CallResponse {
  call_id: string;
  status: 'initiated' | 'in-progress' | 'completed' | 'failed';
  from_number: string;
  to_number: string;
  flow_url: string;
  timestamp: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
}

export interface CallHistoryItem extends CallResponse {
  id: number;
}

// New types for AI Configuration
export interface AIConfigUpdateRequest {
  selected_llm_service: 'ollama' | 'claude';
  ollama_model?: string; // Optional override for Ollama model
  claude_model?: string; // Optional override for Claude model
}

export interface AIConfigResponse {
  selected_llm_service: 'ollama' | 'claude';
  ollama_model?: string; // The saved override model
  claude_model?: string; // The saved override model
  message: string;
}

export interface AIStatusResponse {
  ollama_available: boolean;
  claude_available: boolean;
  ollama_model?: string; // Default Ollama model from environment
  claude_model?: string; // Default Claude model from environment
  ollama_api_url?: string; // Ollama API URL from environment
}
