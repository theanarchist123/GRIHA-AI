"use client";

import { useEffect, useState, useRef } from "react";
import Vapi from "@vapi-ai/web";
import Lottie, { LottieRefCurrentProps } from "lottie-react";
import { Mic, MicOff, User, Bot, Building2, MapPin, IndianRupee } from "lucide-react";
import { useUser } from "@clerk/nextjs";
import Link from "next/link";
import soundwavesAnimation from "@/lib/soundwaves.json";
import { formatPrice } from "@/lib/utils";
import { DashboardSidebar } from "@/components/shared/Navbar";

// Pass the key to Vapi directly as requested by the user
const vapi = new Vapi("8fbe3d07-6861-4876-854d-9d79263a5841");

export default function NegotiatePage({ params }: { params: { id: string } }) {
  const { user, isLoaded } = useUser();
  const userName = user?.fullName || user?.primaryEmailAddress?.emailAddress?.split("@")[0] || "Guest";
  
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [property, setProperty] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [transcript, setTranscript] = useState("");
  const [speaker, setSpeaker] = useState<"assistant" | "user" | "">("");
  const [fullTranscript, setFullTranscript] = useState<{role: string, content: string}[]>([]);
  const lottieRef = useRef<LottieRefCurrentProps>(null);
  const propertyRef = useRef<any>(null); // To access property in event listeners

  // Fetch property details on mount
  useEffect(() => {
    const fetchProperty = async () => {
      try {
        const res = await fetch(`http://localhost:10000/api/properties/${params.id}`);
        if (res.ok) {
          const json = await res.json();
          setProperty(json.data);
          propertyRef.current = json.data;
        }
      } catch (err) {
        console.error("Failed to fetch property", err);
      } finally {
        setLoading(false);
      }
    };
    fetchProperty();
  }, [params.id]);

  useEffect(() => {
    // Sync Lottie playback speed to agent voice volume in real-time
    vapi.on("volume-level", (level: number) => {
      if (lottieRef.current) {
        if (level > 0.01) {
          lottieRef.current.play();
          // Map volume (0–1) to animation speed (0.5–3x) for visual sync
          const speed = 0.5 + level * 3;
          lottieRef.current.setSpeed(speed);
          setAgentSpeaking(true);
        } else {
          // Slow to idle when quiet
          lottieRef.current.setSpeed(0.5);
          setAgentSpeaking(false);
        }
      }
    });

    vapi.on("speech-start", () => {
      setAgentSpeaking(true);
      if (lottieRef.current) {
        lottieRef.current.play();
        lottieRef.current.setSpeed(1.5);
      }
    });

    vapi.on("speech-end", () => {
      setAgentSpeaking(false);
      if (lottieRef.current) {
        lottieRef.current.setSpeed(0.4);
      }
    });

    vapi.on("call-start", () => {
      setConnecting(false);
      setIsSessionActive(true);
      if (lottieRef.current) {
        lottieRef.current.play();
        lottieRef.current.setSpeed(0.5);
      }
    });

    vapi.on("call-end", () => {
      setConnecting(false);
      setIsSessionActive(false);
      setAgentSpeaking(false);
      if (lottieRef.current) lottieRef.current.stop();

      // Save transcript
      setFullTranscript((currentTranscript) => {
        if (currentTranscript.length > 0 && propertyRef.current) {
          const pName = propertyRef.current?.apartmentName || propertyRef.current?.title || "the property";
          fetch("http://localhost:10000/api/documents/save-transcript", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              property_id: propertyRef.current.id,
              property_context: pName,
              clerk_id: user?.id,
              transcript: currentTranscript
            })
          })
          .then(res => res.json())
          .then(data => console.log("Transcript saved:", data))
          .catch(err => console.error("Failed to save transcript:", err));
        }
        return []; // Clear for next call
      });
    });

    vapi.on("message", (msg: any) => {
      if (msg.type === "transcript") {
        setTranscript(msg.transcript || "");
        setSpeaker(msg.role === "assistant" ? "assistant" : "user");
        
        if (msg.transcriptType === "final" && msg.transcript) {
          setFullTranscript((prev) => [...prev, { role: msg.role === "assistant" ? "assistant" : "user", content: msg.transcript }]);
        }
      }
    });

    vapi.on("error", (e) => {
      console.error(e);
      setConnecting(false);
    });

    return () => {
      vapi.stop();
    };
  }, []);

  const toggleSession = async () => {
    if (isSessionActive) {
      vapi.stop();
      setIsSessionActive(false);
    } else {
      setConnecting(true);
      try {
        const pName = property?.apartmentName || property?.title || "the property";
        const pLoc = property?.locality || property?.city || "the requested location";
        const pPrice = property?.price ? `₹${property.price}/month` : "the listed price";
        
        await vapi.start("4449c0b9-eed0-4880-badd-9043b3f3889e", {
          firstMessage: `Hi ${userName}! I am the Griha AI broker representing ${pName}. How can I assist you with your negotiation today?`,
          model: {
            provider: "openai",
            model: "gpt-3.5-turbo",
            messages: [
              {
                role: "system",
                content: `You are an expert real estate broker representing the property "${pName}" located in "${pLoc}". The asking rent is ${pPrice}. The prospective tenant's name is ${userName}. Act as a tough but helpful negotiator. Do not give away the property easily, but be willing to compromise on brokerage or security deposit if the tenant is serious.`
              }
            ]
          }
        });
      } catch (e) {
        console.error("Failed to start Vapi", e);
        setConnecting(false);
      }
    }
  };

  const toggleMic = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    vapi.setMuted(nextMuted);
  };

  if (loading) {
    return <div className="min-h-screen bg-cream flex items-center justify-center font-sans">Loading...</div>;
  }

  const pName = property?.apartmentName || property?.title || "Property";
  const pLoc = property?.locality || property?.city || "Location";
  const pPrice = property?.price ? formatPrice(property.price) : "Price";
  const pImage = property?.images?.[0] || "";

  return (
    <div className="min-h-screen bg-cream font-sans">
      <DashboardSidebar />
      <div className="pl-[260px] min-h-screen flex items-center justify-center px-6 py-8">
      <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Left Panel: AI Agent (Takes up 2/3 of space to allow side panel to breathe) */}
        <div className="md:col-span-2 flex flex-col items-center justify-center p-12 border border-warm-gold/50 rounded-2xl bg-white shadow-sm relative min-h-[600px] overflow-hidden">
          
          <div className="relative w-72 h-72 flex items-center justify-center mb-8">
            {isSessionActive ? (
              /* Active: Lottie IS the focal point — controlled via lottieRef for voice sync */
              <Lottie 
                lottieRef={lottieRef}
                animationData={soundwavesAnimation} 
                loop={true} 
                autoplay={false}
                style={{ width: "100%", height: "100%" }}
              />
            ) : (
              /* Idle: Just show the Bot icon with a soft ring */
              <>
                <div className="absolute inset-0 rounded-full bg-gray-100 opacity-60" />
                <div className="absolute inset-6 rounded-full bg-gray-200 opacity-50" />
                <div className="relative z-10 w-32 h-32 bg-charcoal rounded-full flex items-center justify-center shadow-2xl border-[4px] border-warm-gold">
                  <Bot className="w-16 h-16 text-warm-gold" />
                </div>
              </>
            )}
          </div>
          
          <h1 className="text-3xl font-dm font-bold text-charcoal tracking-tight">Griha AI Broker</h1>
          <p className="text-muted text-lg mt-3">{pName}</p>
          
          {connecting && <p className="text-warm-gold font-bold text-sm mt-6 font-dm animate-pulse tracking-widest uppercase">Connecting securely...</p>}

          {/* Live Caption / Transcript */}
          {isSessionActive && transcript && (
            <div className="mt-8 w-full max-w-lg">
              <div className={`px-5 py-4 rounded-2xl text-center transition-all duration-300 ${
                speaker === "assistant"
                  ? "bg-charcoal/5 border border-charcoal/10"
                  : "bg-forest/5 border border-forest/20"
              }`}>
                <p className={`text-xs font-bold uppercase tracking-widest mb-2 ${
                  speaker === "assistant" ? "text-warm-gold" : "text-forest"
                }`}>
                  {speaker === "assistant" ? "Broker" : "You"}
                </p>
                <p className="text-charcoal font-dm text-base leading-relaxed">{transcript}</p>
              </div>
            </div>
          )}
        </div>

        {/* Right Panel: Context & Controls (Takes up 1/3 space) */}
        <div className="flex flex-col gap-4">
          
          {/* Box 1: User Profile */}
          <div className="bg-white rounded-2xl p-6 border border-charcoal/10 shadow-sm flex flex-col items-center justify-center h-48">
            {isLoaded && user?.imageUrl ? (
              <img src={user.imageUrl} alt={userName} className="w-20 h-20 rounded-full mb-4 shadow-md border-2 border-forest object-cover" />
            ) : (
              <div className="w-20 h-20 rounded-full bg-forest/10 flex items-center justify-center mb-4 border-2 border-forest text-forest shadow-md">
                <User className="w-10 h-10" />
              </div>
            )}
            <h2 className="text-lg font-dm font-bold text-charcoal">{userName}</h2>
          </div>
          
          {/* Box 2: Controls */}
          <div className="bg-white rounded-2xl p-6 border border-charcoal/10 shadow-sm flex flex-col gap-4">
            <button 
              onClick={toggleMic}
              disabled={!isSessionActive}
              className={`w-full py-3 rounded-xl border flex flex-col items-center justify-center gap-2 transition-all ${
                !isSessionActive ? "opacity-50 cursor-not-allowed bg-gray-50 border-gray-200" :
                isMuted ? "bg-red-50 border-red-200 text-red-600" : "bg-white border-charcoal/20 text-charcoal hover:bg-gray-50 hover:shadow-sm"
              }`}
            >
              {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
              <span className="text-sm font-dm font-medium">{isMuted ? "Turn on microphone" : "Turn off microphone"}</span>
            </button>
            
            <button 
              onClick={toggleSession}
              disabled={connecting}
              className={`w-full py-4 rounded-xl text-white font-dm font-bold text-lg transition-all shadow-md ${
                isSessionActive ? "bg-[#C00000] hover:bg-red-700" : "bg-charcoal hover:bg-black"
              }`}
            >
              {connecting ? "Connecting..." : (isSessionActive ? "End Session" : "Start Session")}
            </button>
          </div>

          {/* Box 3: Property Details */}
          <div className="bg-white rounded-2xl p-6 border border-charcoal/10 shadow-sm flex flex-col flex-1">
            <h3 className="font-dm font-bold text-charcoal text-sm uppercase tracking-wider mb-4 border-b pb-2">Property Details</h3>
            
            {pImage && (
              <div className="w-full h-32 rounded-xl bg-gray-100 mb-4 overflow-hidden border">
                <img src={pImage} alt={pName} className="w-full h-full object-cover" />
              </div>
            )}
            
            <div className="space-y-3">
              <div className="flex items-start gap-3">
                <Building2 className="w-5 h-5 text-warm-gold shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs text-muted uppercase tracking-wider">Property</p>
                  <p className="font-medium text-sm text-charcoal">{pName}</p>
                </div>
              </div>
              
              <div className="flex items-start gap-3">
                <MapPin className="w-5 h-5 text-warm-gold shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs text-muted uppercase tracking-wider">Location</p>
                  <p className="font-medium text-sm text-charcoal">{pLoc}</p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <IndianRupee className="w-5 h-5 text-warm-gold shrink-0 mt-0.5" />
                <div>
                  <p className="text-xs text-muted uppercase tracking-wider">Asking Rent</p>
                  <p className="font-bold text-sm text-forest">{pPrice}/mo</p>
                </div>
              </div>
            </div>
            
            <div className="mt-auto pt-6 text-center">
              <Link href={`/property/${params.id}`} className="text-xs font-dm text-muted hover:text-charcoal hover:underline">
                Return to full listing
              </Link>
            </div>
          </div>
          
        </div>
      </div>
      </div>
    </div>
  );
}
