import { useConversation } from "@elevenlabs/react";

export function useMyAgent(onTranscript: (evt: any) => void) {
  return useConversation({
    onMessage: (evt: any) => {
      // Listen for final transcriptions from the AI
      if (evt.type === "transcription" && evt.isFinal && evt.text) {
        onTranscript(evt);
      }
    },
    onAudio: (audioUrl: string) => {
      // Play back any audio URL from the AI
      const audio = new Audio(audioUrl);
      audio.play().catch(err => {
        console.warn("Audio playback failed:", err);
      });
    },
    onError: (err: any) => {
      console.error("ElevenLabs Agent Error:", err);
    },
    onConnect: () => {
      console.log("Connected to ElevenLabs agent");
    },
    onDisconnect: () => {
      console.log("Disconnected from ElevenLabs agent");
    },
  });
}
