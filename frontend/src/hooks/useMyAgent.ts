
import { useConversation } from "@elevenlabs/react";

export function useMyAgent(onTranscript: (evt: any) => void) {
  return useConversation({
    onMessage: (evt: any) => {
      if (evt.type === "user_transcript" && evt.user_transcript?.text) {
        onTranscript({ text: evt.user_transcript.text });
      }
    },
    onConnect: () => {
      console.log("Connected to ElevenLabs agent");
    },
    onDisconnect: () => {
      console.log("Disconnected from ElevenLabs agent");
    },
    onError: (err: any) => {
      console.error("ElevenLabs Agent Error:", err);
    },
  });
}
