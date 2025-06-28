// src/pages/AgentChat.tsx
import React, { useState } from 'react';
import { useMyAgent } from '../hooks/useMyAgent';

const AgentChat = () => {
  const [transcript, setTranscript] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const convo = useMyAgent(evt => {
    setTranscript(t => t + `\nUser: ${evt.text}`);
  });

  const startInterview = async () => {
    const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const id = await convo.startSession({
      agentId: 'agent_01jyv4f4b3fv1s5fhysv8sh82b', // ✅ Your agent ID
      userAudioStream: micStream,
      dynamicVariables: {
        job_summary: "Built a project management dashboard using React, Supabase, and Tailwind.",
        question_count: 2,
      },
    });

    (convo as any).micStream = micStream;
    setSessionId(id);
    setIsConnected(true);
    console.log('🎤 Voice session started:', id);
  };

  const endInterview = () => {
    convo.endSession();
    const mic = (convo as any).micStream as MediaStream;
    mic?.getTracks().forEach(t => t.stop());
    setIsConnected(false);
    console.log('🛑 Session ended');
  };

  return (
    <div className="max-w-xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Real-Time Voice Interview</h1>
      <button
        onClick={startInterview}
        className="px-4 py-2 bg-blue-600 text-white rounded mr-2"
        disabled={isConnected}
      >
        Start Interview
      </button>
      <button
        onClick={endInterview}
        className="px-4 py-2 bg-red-600 text-white rounded"
        disabled={!isConnected}
      >
        End Interview
      </button>
      <pre className="mt-6 bg-gray-100 p-4 rounded whitespace-pre-wrap text-sm">{transcript}</pre>
    </div>
  );
};

export default AgentChat;
