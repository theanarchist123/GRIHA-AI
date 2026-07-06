"use client";

import { useEffect, useState, useRef } from "react";
import Vapi from "@vapi-ai/web";
import Lottie, { LottieRefCurrentProps } from "lottie-react";
import { Mic, MicOff, Repeat, PhoneOff } from "lucide-react";

// In Next.js, importing JSON from outside the project root can be tricky. 
// We will just fetch it or we copy it to public folder.
// For now we will try to fetch it from a relative public path or require it if it's copied.
import soundwavesAnimation from "../../../soundwaves.json";

const vapi = new Vapi(process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY || "dummy_key");

export default function NegotiatePage({ params }: { params: { id: string } }) {
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("Connecting to Griha AI...");
  const lottieRef = useRef<LottieRefCurrentProps>(null);

  useEffect(() => {
    const startVapi = async () => {
      try {
        await vapi.start("dummy-assistant-id"); 
        setIsSessionActive(true);
        setTranscript("Hi! I am Griha AI, your negotiation assistant. How can I help you today?");
      } catch (e) {
        console.error("Vapi start error", e);
      }
    };
    
    // startVapi(); // Uncomment in production

    vapi.on("speech-start", () => {
      setAgentSpeaking(true);
      if (lottieRef.current) {
        lottieRef.current.play();
      }
    });

    vapi.on("speech-end", () => {
      setAgentSpeaking(false);
      if (lottieRef.current) {
        lottieRef.current.stop();
      }
    });

    vapi.on("message", (message: any) => {
      if (message.type === "transcript" && message.transcriptType === "final") {
        setTranscript(message.transcript || "");
      }
    });

    return () => {
      vapi.stop();
    };
  }, []);

  const toggleMic = () => {
    setIsMuted(!isMuted);
    vapi.setMuted(!isMuted);
  };

  const endNegotiation = () => {
    vapi.stop();
    setIsSessionActive(false);
    window.location.href = `/property/${params.id}`;
  };

  const repeatLast = () => {
    vapi.send({ type: "add-message", message: { role: "user", content: "Can you please repeat that?" } });
  };

  return (
    <div className="min-h-screen bg-cream flex items-center justify-center p-6 font-sans">
      <div className="max-w-6xl w-full grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Left Panel: AI Agent */}
        <div className="md:col-span-2 flex flex-col items-center justify-center p-12 border border-border-custom rounded-2xl bg-surface shadow-sm relative min-h-[500px]">
          
          <div className="bg-sand w-40 h-40 rounded-full flex items-center justify-center mb-8 border border-border-custom overflow-hidden shadow-sm">
            <Lottie 
              lottieRef={lottieRef}
              animationData={soundwavesAnimation} 
              loop={true} 
              autoplay={false}
              style={{ width: 150, height: 150, opacity: agentSpeaking ? 1 : 0.4 }}
            />
          </div>
          
          <h1 className="text-3xl font-playfair text-charcoal mb-12">Griha AI Negotiation Agent</h1>
          
          <div className="text-center px-12 mt-8 min-h-[100px] flex items-center justify-center">
            <p className="text-xl text-charcoal leading-relaxed font-dm">
              {transcript}
            </p>
          </div>
          
          <div className="absolute bottom-12 flex items-center gap-6">
            <button 
              onClick={repeatLast}
              className="w-12 h-12 flex items-center justify-center rounded-full bg-cream border border-border-custom text-charcoal hover:bg-sand transition-all shadow-sm"
              title="Repeat last message"
            >
              <Repeat className="w-5 h-5" />
            </button>
            <button 
              onClick={endNegotiation}
              className="w-16 h-16 flex items-center justify-center rounded-full bg-red-500 text-white hover:bg-red-600 transition-all shadow-md"
              title="End Negotiation"
            >
              <PhoneOff className="w-6 h-6" />
            </button>
            <button 
              onClick={toggleMic}
              className={`w-12 h-12 flex items-center justify-center rounded-full border border-border-custom transition-all shadow-sm ${
                isMuted ? "bg-red-50 text-red-500" : "bg-cream text-charcoal hover:bg-sand"
              }`}
              title={isMuted ? "Unmute" : "Mute"}
            >
              {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Right Panel: Call Context */}
        <div className="flex flex-col gap-6">
          <div className="bg-surface rounded-2xl p-6 border border-border-custom shadow-sm flex flex-col items-center">
            <div className="w-full aspect-video rounded-xl bg-sand mb-4 flex items-center justify-center overflow-hidden border border-border-custom">
                <span className="text-muted font-playfair italic">Selected Property</span>
            </div>
            <h3 className="font-playfair text-xl text-charcoal mb-2">Live Session</h3>
            <p className="text-muted text-sm text-center font-dm mb-4">
              AI is ready to assist you
            </p>
          </div>
          
          <div className="bg-surface rounded-2xl p-6 border border-border-custom shadow-sm flex-1">
            <h4 className="font-dm font-semibold text-charcoal mb-4 uppercase tracking-wider text-xs">Suggested Topics</h4>
            <ul className="space-y-4 text-sm text-charcoal font-dm">
              <li className="flex items-start gap-3">
                <div className="w-2 h-2 mt-1.5 rounded-full bg-forest shrink-0" />
                <span>Rent reduction negotiation.</span>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-2 h-2 mt-1.5 rounded-full bg-forest shrink-0" />
                <span>Brokerage fee waivers.</span>
              </li>
              <li className="flex items-start gap-3">
                <div className="w-2 h-2 mt-1.5 rounded-full bg-forest shrink-0" />
                <span>Security deposit terms.</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
