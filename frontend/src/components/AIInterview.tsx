import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Mic, MicOff, ArrowLeft } from "lucide-react";
import { Job } from "@/types";
import { useToast } from "@/hooks/use-toast";
import { useMyAgent } from "@/hooks/useMyAgent";

interface AIInterviewProps {
  job: Job;
  onBack: () => void;
}

const AIInterview = ({ job, onBack }: AIInterviewProps) => {
  const [transcript, setTranscript] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const { toast } = useToast();

  const convo = useMyAgent(evt => {
    setTranscript(t => t + `\nUser: ${evt.text}`);
  });

  const startInterview = async () => {
    try {
      // Request microphone permission and get stream
      const micStream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Start session with mic stream and dynamicVariables (passing job description)
      const id = await convo.startSession({
        agentId: 'agent_01jyv4f4b3fv1s5fhysv8sh82b',
        userAudioStream: micStream,
        dynamicVariables: {
          job_summary: job.description,
          question_count: 2,  // example variable, you can change or remove if unused
        },
        // Optional: you can still add prompt overrides if your backend supports it
        // overrides: {
        //   agent: {
        //     firstMessage: "Hello! I'm your AI interviewer today. Let's start with you telling me about yourself and your relevant experience for this position."
        //   }
        // }
      });

      // Store micStream so you can stop it on end
      (convo as any).micStream = micStream;

      setSessionId(id);
      setIsConnected(true);
      console.log('🎤 Voice session started:', id);

      toast({
        title: "Interview Started",
        description: "AI interviewer is ready. Start speaking to respond.",
      });
    } catch (error) {
      console.error("Error starting interview:", error);
      toast({
        title: "Error",
        description: "Failed to start interview. Please check microphone permissions.",
        variant: "destructive",
      });
    }
  };

  const endInterview = async () => {
    try {
      await convo.endSession();

      // Stop all tracks in micStream
      const mic = (convo as any).micStream as MediaStream;
      mic?.getTracks().forEach(track => track.stop());

      setIsConnected(false);
      setSessionId(null);
      console.log('🛑 Session ended');

      toast({
        title: "Interview Ended",
        description: "Voice interview session has been completed.",
      });
    } catch (error) {
      console.error("Error ending interview:", error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Search
        </Button>
        <div>
          <h2 className="text-2xl font-bold text-gray-900">AI Voice Interview</h2>
          <p className="text-gray-600">Real-time voice conversation with AI interviewer</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Interview Setup</CardTitle>
          <CardDescription>
            Voice-powered interview customized for this job opportunity
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="bg-blue-50 p-4 rounded-lg mb-6">
            <h4 className="font-semibold text-blue-900 mb-2">Job Description:</h4>
            <p className="text-blue-800 text-sm">{job.description}</p>
          </div>

          <div className="flex flex-col items-center space-y-6">
            <div className="text-center">
              <Button
                onClick={isConnected ? endInterview : startInterview}
                size="lg"
                variant={isConnected ? "destructive" : "default"}
                className="rounded-full w-20 h-20"
                disabled={false}
              >
                {isConnected ? (
                  <MicOff className="w-8 h-8" />
                ) : (
                  <Mic className="w-8 h-8" />
                )}
              </Button>
              <p className="text-gray-600 mt-2">
                {isConnected ? "Click to end interview" : "Click to start voice interview"}
              </p>
              {sessionId && (
                <p className="text-xs text-gray-500 mt-1">Session: {sessionId}</p>
              )}
            </div>

            {isConnected && (
              <div className="w-full max-w-md">
                <div className="bg-green-50 p-3 rounded-lg text-center">
                  <div className="w-3 h-3 bg-green-500 rounded-full mx-auto mb-2 animate-pulse"></div>
                  <p className="text-green-800 text-sm font-medium">Live Interview Active</p>
                  <p className="text-green-600 text-xs">Speak naturally - AI is listening</p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {transcript && (
        <Card>
          <CardHeader>
            <CardTitle>Conversation Transcript</CardTitle>
            <CardDescription>
              Real-time transcript of your interview conversation
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="bg-gray-100 p-4 rounded whitespace-pre-wrap text-sm max-h-64 overflow-y-auto">
              {transcript}
            </pre>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Voice Interview Experience</CardTitle>
          <CardDescription>
            Powered by ElevenLabs AI voice technology
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm text-gray-600">
            <p>• The AI interviewer will ask questions based on the job description</p>
            <p>• Speak naturally and clearly for best results</p>
            <p>• The interview will be conversational and adaptive</p>
            <p>• Make sure your microphone is working before starting</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default AIInterview;
