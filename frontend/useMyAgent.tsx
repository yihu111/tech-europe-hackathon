// src/hooks/useMyAgent.ts
import { useConversation } from "@elevenlabs/react";

export function useMyAgent(onTranscript: (evt: any) => void) {
  return useConversation({
    onMessage: (evt: any) => {
      if (evt.type === "transcription" && evt.isFinal && evt.text) {
        onTranscript(evt);
      }
    },
    onAudio: (audioUrl: string) => {
      const audio = new Audio(audioUrl);
      audio.play().catch(err => {
        console.warn("Audio playback failed:", err);
      });
    },
    onError: (err: any) => {
      console.error("ElevenLabs Agent Error:", err);
    },
  });
}
