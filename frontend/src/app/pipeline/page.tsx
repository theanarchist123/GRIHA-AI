"use client";

import { useState, useEffect } from "react";
import { Search, Filter, Plus, MapPin, Sparkles } from "lucide-react";
import Link from "next/link";
import { DashboardSidebar, DashboardTopBar } from "@/components/shared/Navbar";
import { motion } from "framer-motion";

type PipelineItem = {
  id: string;
  property_id: string;
  title: string;
  location: string;
  price: string;
  image: string;
};

type PipelineData = {
  shortlisted: PipelineItem[];
  underReview: PipelineItem[];
  negotiating: PipelineItem[];
  offerMade: PipelineItem[];
};

const COLUMNS = [
  { id: "shortlisted", label: "Shortlisted", dotColor: "bg-forest" },
  { id: "underReview", label: "Under Review", dotColor: "bg-warm-gold" },
  { id: "negotiating", label: "Negotiating", dotColor: "bg-blue-500" },
  { id: "offerMade", label: "Offer Made", dotColor: "bg-emerald-500" },
] as const;

export default function PipelinePage() {
  const [data, setData] = useState<PipelineData>({
    shortlisted: [],
    underReview: [],
    negotiating: [],
    offerMade: []
  });
  const [loading, setLoading] = useState(true);
  
  // Drag state
  const [draggedItem, setDraggedItem] = useState<{ id: string, sourceCol: string } | null>(null);

  useEffect(() => {
    fetchPipeline();
  }, []);

  const fetchPipeline = async () => {
    try {
      let res;
      let retryCount = 0;
      while (retryCount < 3) {
        try {
          res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/pipeline`);
          break;
        } catch (err) {
          retryCount++;
          if (retryCount >= 3) throw err;
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }
      if (!res) throw new Error("Failed to fetch after retries");
      const json = await res.json();
      if (json.status === "success") {
        setData(json.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDragStart = (e: React.DragEvent, id: string, sourceCol: string) => {
    setDraggedItem({ id, sourceCol });
    // This makes the drag image look better in some browsers
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault(); // Necessary to allow dropping
    e.dataTransfer.dropEffect = "move";
  };

  const handleDrop = async (e: React.DragEvent, targetCol: string) => {
    e.preventDefault();
    if (!draggedItem || draggedItem.sourceCol === targetCol) {
      setDraggedItem(null);
      return;
    }

    const { id, sourceCol } = draggedItem;
    
    // Optimistic UI update
    setData((prev) => {
      const newData = { ...prev };
      const itemIndex = newData[sourceCol as keyof PipelineData].findIndex(i => i.id === id);
      if (itemIndex > -1) {
        const item = newData[sourceCol as keyof PipelineData][itemIndex];
        newData[sourceCol as keyof PipelineData] = newData[sourceCol as keyof PipelineData].filter(i => i.id !== id);
        newData[targetCol as keyof PipelineData] = [...newData[targetCol as keyof PipelineData], item];
      }
      return newData;
    });

    setDraggedItem(null);

    // Persist to backend
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/pipeline/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: targetCol })
      });
    } catch (err) {
      console.error("Failed to update status", err);
      // Optional: rollback on failure
      fetchPipeline();
    }
  };

  return (
    <div className="min-h-screen bg-cream flex font-sans">
      <DashboardSidebar />
      <div className="ml-[260px] flex-1 flex flex-col relative">
        <DashboardTopBar />

        {/* Header */}
        <header className="px-6 py-6 flex items-center justify-between border-b border-border-custom bg-surface sticky top-0 z-10">
          <div>
            <h1 className="text-3xl font-playfair text-charcoal">My Pipeline</h1>
            <p className="text-muted text-sm font-dm mt-1">Track and manage your shortlisted properties</p>
          </div>
          
          <div className="flex gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" size={18} />
              <input 
                id="pipeline-search"
                name="pipeline-search"
                type="text" 
                placeholder="Search properties..." 
                className="pl-10 pr-4 py-2 bg-cream border border-border-custom rounded-lg text-sm text-charcoal focus:ring-2 focus:ring-forest outline-none font-dm"
              />
            </div>
            <button className="flex items-center gap-2 px-4 py-2 bg-transparent border border-border-custom rounded-lg text-sm font-medium text-charcoal hover:bg-cream transition-colors font-dm">
              <Filter size={16} /> Filter
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-forest text-cream rounded-lg text-sm font-medium hover:bg-forest-light transition-colors font-dm">
              <Plus size={16} /> Add Property
            </button>
          </div>
        </header>

        {/* Kanban Board */}
        <main className="flex-1 overflow-x-auto p-6 bg-cream">
          {loading ? (
            <div className="flex justify-center mt-20"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-forest"></div></div>
          ) : (
            <div className="flex gap-6 min-w-max h-full pb-20">
              {COLUMNS.map(col => (
                <div 
                  key={col.id} 
                  className="w-80 flex flex-col gap-4 bg-white border border-border-custom rounded-xl p-4 min-h-[60vh]"
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, col.id)}
                >
                  <div className="flex items-center justify-between pb-3 border-b border-border-custom border-dashed">
                    <div className="flex items-center gap-2">
                      <div className={`w-2.5 h-2.5 rounded-full ${col.dotColor}`}></div>
                      <h2 className="font-bold font-dm text-charcoal">{col.label}</h2>
                    </div>
                    <span className="bg-sand text-forest px-2 py-0.5 rounded-md text-xs font-bold">{data[col.id as keyof PipelineData].length}</span>
                  </div>
                  
                  <div className="flex-1 flex flex-col gap-4">
                    {data[col.id as keyof PipelineData].map(prop => (
                      <div 
                        key={prop.id}
                        draggable
                        onDragStart={(e) => handleDragStart(e, prop.id, col.id)}
                        className="bg-surface border border-border-custom rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow cursor-grab active:cursor-grabbing"
                      >
                        <Link href={`/property/${prop.property_id}`}>
                          <div className="h-32 w-full bg-sand relative overflow-hidden">
                            <img src={prop.image} alt={prop.title} className="w-full h-full object-cover" draggable={false} />
                          </div>
                          
                          <div className="p-4">
                            <h3 className="font-bold font-dm text-charcoal text-sm leading-tight mb-1">{prop.title}</h3>
                            <p className="text-muted text-xs font-dm mb-2">{prop.location}</p>
                            <p className="font-bold text-forest text-sm">{prop.price}</p>
                          </div>
                        </Link>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </main>

        {/* Floating Action Button exactly like the screenshot */}
        <div className="fixed bottom-6 right-6 z-50">
          <button className="bg-forest text-white p-4 rounded-full shadow-lg hover:bg-forest-light transition-colors">
            <Sparkles className="w-6 h-6" />
          </button>
        </div>
      </div>
    </div>
  );
}
