"use client";

import { useEffect, useState, useRef } from "react";
import { Terminal, Loader2, X } from "lucide-react";

export default function LiveAgentTerminal({ onClose, hunt }: { onClose: () => void, hunt: any }) {
  const [status, setStatus] = useState("Initializing deep research agent...");
  const [actions, setActions] = useState<{text: string, time: number, type: string}[]>([]);
  const imgRef = useRef<HTMLImageElement>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [actions]);

  useEffect(() => {
    if (!hunt) return;

    setActions([{ text: "Connecting to Intelligence Cluster...", time: Date.now(), type: 'info' }]);
    
    const wsUrl = `${process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") || "ws://127.0.0.1:10000"}/ws/browser-stream/${hunt.id}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setActions(prev => [...prev, { text: "WebSocket connection established.", time: Date.now(), type: 'info' }]);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "frame") {
          if (imgRef.current) {
            imgRef.current.src = data.image;
          }
        } else if (data.type === "status") {
          setStatus(data.message);
          setActions(prev => [...prev, { text: data.message, time: Date.now(), type: 'info' }]);
        } else if (data.type === "action") {
          setActions(prev => [...prev, { text: data.message, time: Date.now(), type: 'action' }]);
        } else if (data.type === "data") {
          setActions(prev => [...prev, { text: JSON.stringify(data.data), time: Date.now(), type: 'data' }]);
        } else if (data.type === "error") {
          setActions(prev => [...prev, { text: data.message, time: Date.now(), type: 'error' }]);
        }
      } catch (e) {
        console.error(e);
      }
    };

    ws.onerror = (e) => {
      setActions(prev => [...prev, { text: "WebSocket error occurred.", time: Date.now(), type: 'error' }]);
    };

    return () => {
      ws.close();
    };
  }, [hunt]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
      <div className="bg-[#0D1117] w-full max-w-6xl h-[85vh] rounded-xl border border-gray-800 shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 bg-[#161B22] border-b border-gray-800">
          <div className="flex items-center gap-3">
            <Terminal className="w-5 h-5 text-green-500" />
            <h2 className="text-white font-medium">Autopilot Intelligence Stream</h2>
            <div className="flex items-center gap-2 px-2 py-1 rounded bg-gray-800 text-xs text-gray-300">
              <Loader2 className="w-3 h-3 animate-spin" />
              {status}
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-white rounded hover:bg-gray-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Main Visualizer */}
          <div className="flex-1 bg-black flex items-center justify-center relative border-r border-gray-800">
            {/* Direct image ref for maximum performance without React render cycle */}
            <img 
              ref={imgRef} 
              className="max-w-full max-h-full object-contain"
              alt="Browser Stream" 
            />
          </div>

          {/* Activity Log */}
          <div className="w-96 bg-[#0D1117] flex flex-col font-mono text-sm overflow-hidden">
            <div className="p-2 border-b border-gray-800 bg-[#161B22] text-xs text-gray-400 font-semibold uppercase tracking-wider">
              Execution Log
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {actions.map((act, i) => (
                <div key={i} className={`flex items-start gap-2 ${act.type === 'error' ? 'text-red-400' : act.type === 'action' ? 'text-blue-400' : 'text-gray-300'}`}>
                  <span className="text-gray-600 text-xs mt-0.5">
                    {new Date(act.time).toLocaleTimeString([], { hour12: false })}
                  </span>
                  <div className="flex-1 whitespace-pre-wrap">{act.text}</div>
                </div>
              ))}
              <div ref={logEndRef} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
