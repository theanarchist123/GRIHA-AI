"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Bot, User, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface PointOfInterest {
  name: string;
  lat: number;
  lng: number;
  distance_m: number;
  tags?: Record<string, string>;
}

interface Message {
  id: string;
  role: "user" | "bot";
  text: string;
}

interface NeighbourhoodChatProps {
  propertyId: string;
  onUpdateMap: (center: any, markers: PointOfInterest[]) => void;
}

export default function NeighbourhoodChat({ propertyId, onUpdateMap }: NeighbourhoodChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "init",
      role: "bot",
      text: "Hi! I'm your Griha AI Neighbourhood Explorer. Ask me anything about this area—like 'Where are the nearest hospitals?' or 'Find me some good parks within 2km'."
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", text: input.trim() };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch("http://localhost:10000/api/neighbourhood/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ property_id: propertyId, query: userMsg.text }),
      });
      const data = await res.json();
      
      if (data.status === "success") {
        const botMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: "bot",
          text: data.data.answer
        };
        setMessages(prev => [...prev, botMsg]);
        
        // Update map
        if (data.data.property_center && data.data.markers) {
          onUpdateMap(data.data.property_center, data.data.markers);
        }
      } else {
        throw new Error(data.detail || "API Error");
      }
    } catch (err: any) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 2).toString(),
        role: "bot",
        text: "Sorry, I ran into an error trying to fetch that information. Please try again."
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-dark-bg border border-dark-border rounded-2xl overflow-hidden shadow-sm">
      <div className="p-4 border-b border-dark-border bg-dark-bg/50 backdrop-blur-sm">
        <h2 className="font-playfair text-xl text-white flex items-center gap-2">
          <Bot className="w-5 h-5 text-warm-gold" /> Neighbourhood AI
        </h2>
        <p className="text-xs text-dark-text font-dm mt-1">Powered by Gemini & OpenStreetMap</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              <div className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center ${
                msg.role === "user" ? "bg-warm-gold/20 text-warm-gold" : "bg-dark-card border border-dark-border text-warm-gold"
              }`}>
                {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div className={`px-4 py-3 rounded-2xl max-w-[80%] ${
                msg.role === "user" 
                  ? "bg-warm-gold text-dark-bg rounded-tr-sm" 
                  : "bg-dark-card border border-dark-border text-white rounded-tl-sm"
              }`}>
                <p className="text-sm font-dm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {isLoading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
            <div className="w-8 h-8 shrink-0 rounded-full bg-dark-card border border-dark-border text-warm-gold flex items-center justify-center">
              <Loader2 className="w-4 h-4 animate-spin" />
            </div>
            <div className="px-4 py-3 rounded-2xl bg-dark-card border border-dark-border text-white rounded-tl-sm flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-warm-gold animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 rounded-full bg-warm-gold animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 rounded-full bg-warm-gold animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </motion.div>
        )}
        <div ref={endOfMessagesRef} />
      </div>

      <div className="p-4 bg-dark-bg/50 border-t border-dark-border">
        <div className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about hospitals, parks, metros..."
            className="w-full bg-dark-card border border-dark-border rounded-full pl-4 pr-12 py-3 text-sm font-dm text-white placeholder-dark-icon focus:outline-none focus:border-warm-gold/50 transition-colors"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-warm-gold text-dark-bg rounded-full hover:bg-yellow-600 disabled:opacity-50 disabled:hover:bg-warm-gold transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
