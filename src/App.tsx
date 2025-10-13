import React, { useState } from 'react';
import { Header } from './components/Header';
import { CallForm } from './components/CallForm';
import { CallHistory } from './components/CallHistory';
import { StatusIndicator } from './components/StatusIndicator';
import { AIStatusIndicator } from './components/AIStatusIndicator';
import { AIConversationPanel } from './components/AIConversationPanel';
import { WebSocketAudioClient } from './components/WebSocketAudioClient';
import { KnowledgeBaseManager } from './components/KnowledgeBaseManager';

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [selectedKnowledgeBaseId, setSelectedKnowledgeBaseId] = useState('');

  const handleCallInitiated = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  const handleKnowledgeBaseChange = (kbId: string) => {
    setSelectedKnowledgeBaseId(kbId);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
      <Header />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6 flex justify-end">
          <StatusIndicator />
          <div className="ml-4">
            <AIStatusIndicator />
          </div>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          <div>
            <CallForm
              onCallInitiated={handleCallInitiated}
              selectedKnowledgeBaseId={selectedKnowledgeBaseId}
              onKnowledgeBaseChange={handleKnowledgeBaseChange}
            />
          </div>

          <div>
            <WebSocketAudioClient
              selectedKnowledgeBaseId={selectedKnowledgeBaseId}
              onKnowledgeBaseChange={handleKnowledgeBaseChange}
            />
          </div>
        </div>

        <div className="mb-8">
          <KnowledgeBaseManager />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div>
            <CallHistory refreshTrigger={refreshTrigger} />
          </div>

          <div>
            <AIConversationPanel
              selectedKnowledgeBaseId={selectedKnowledgeBaseId}
              onKnowledgeBaseChange={handleKnowledgeBaseChange}
            />
          </div>
        </div>

        {/* ✅ Corrected footer closing tag */}
        <footer className="mt-16 text-center text-gray-600">
          <p className="text-sm">
            © 2025 AdrshyamAI Call Service • Built with React & Node.js
          </p>
        </footer>

      </div>
    </div>
  );
}

export default App;
