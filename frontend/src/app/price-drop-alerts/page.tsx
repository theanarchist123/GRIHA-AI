"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { DashboardSidebar, DashboardTopBar } from "@/components/shared/Navbar";
import { MapPin, Star, ChevronDown, RefreshCw, Trash2, Sparkles, TrendingDown } from "lucide-react";

type AlertItem = {
  id: string;
  property_id: string;
  title: string;
  location: string;
  type: string;
  price: string;
  image: string;
  alertTarget: string;
  saveAmount: string;
  status: string;
};

export default function PriceDropAlertsPage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAlerts();
  }, []);

  const fetchAlerts = async () => {
    try {
      let res;
      let retryCount = 0;
      while (retryCount < 3) {
        try {
          res = await fetch("http://localhost:10000/api/alerts");
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
        setAlerts(json.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (property_id: string) => {
    try {
      await fetch(`http://localhost:10000/api/alerts/${property_id}`, {
        method: "DELETE"
      });
      fetchAlerts();
    } catch (err) {
      console.error(err);
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
            <h1 className="text-3xl font-playfair text-charcoal flex items-center gap-3">
              Price Drop Alerts
            </h1>
            <p className="text-muted text-sm font-dm mt-1">Track discounted properties matching your preferences</p>
          </div>
        </header>

        {/* List Board */}
        <main className="flex-1 p-6 bg-cream">
          <div className="max-w-5xl">
            <h2 className="text-xs font-bold text-muted mb-4 uppercase tracking-wider">
              WATCHING ({alerts.length})
            </h2>

            {loading ? (
               <div className="flex justify-center mt-10"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-forest"></div></div>
            ) : alerts.length === 0 ? (
               <div className="text-center py-10 bg-white border border-border-custom rounded-xl">
                 <p className="text-muted font-dm">You are not watching any properties yet.</p>
               </div>
            ) : (
              <div className="flex flex-col gap-4 pb-20">
                {alerts.map((alert) => (
                  <div key={alert.id} className="bg-white border border-border-custom rounded-xl overflow-hidden hover:shadow-sm transition-shadow">
                    
                    {/* Top Row */}
                    <div className="p-4 flex gap-4">
                      {/* Image */}
                      <div className="w-16 h-16 rounded-lg overflow-hidden shrink-0 bg-sand">
                        <img src={alert.image} alt={alert.title} className="w-full h-full object-cover" />
                      </div>
                      
                      {/* Details & Columns */}
                      <div className="flex-1 flex flex-col md:flex-row gap-4 justify-between">
                        {/* Title & Loc */}
                        <div className="flex-1 min-w-[200px]">
                          <Link href={`/property/${alert.property_id}`} className="hover:underline">
                            <h3 className="font-bold font-dm text-charcoal text-sm leading-tight">{alert.title}</h3>
                          </Link>
                          <p className="text-muted text-xs font-dm mt-0.5 flex items-center gap-1">
                            <MapPin size={10} /> {alert.location} · {alert.type}
                          </p>
                        </div>
                        
                        {/* Listed At */}
                        <div className="flex-1 min-w-[100px]">
                          <p className="text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Listed At</p>
                          <p className="font-bold text-charcoal text-sm">{alert.price}</p>
                        </div>
                        
                        {/* Alert Target */}
                        <div className="flex-1 min-w-[100px]">
                          <p className="text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Alert Target</p>
                          <p className="font-bold text-warm-gold text-sm">{alert.alertTarget}</p>
                        </div>
                        
                        {/* Save */}
                        <div className="flex-1 min-w-[120px]">
                          <p className="text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Save</p>
                          <p className="font-bold text-forest text-sm">{alert.saveAmount}</p>
                        </div>
                        
                        {/* Action Pill */}
                        <div className="shrink-0 flex items-start justify-end min-w-[100px]">
                          <div className="flex items-center gap-1 bg-warm-gold/10 text-warm-gold px-2.5 py-1 rounded-full text-xs font-semibold border border-warm-gold/20">
                            <Star size={12} fill="currentColor" /> Watching
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Bottom Row */}
                    <div className="px-4 py-2 bg-surface/50 border-t border-border-custom flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-warm-gold text-xs">→</span>
                        <span className="text-xs font-bold text-muted font-dm">Stable</span>
                      </div>
                      
                      <div className="flex items-center gap-4 text-xs font-dm text-muted">
                        <button className="flex items-center gap-1 hover:text-charcoal transition-colors">
                          <ChevronDown size={14} /> 2 snapshots
                        </button>
                        <button className="flex items-center gap-1 hover:text-charcoal transition-colors font-semibold">
                          <RefreshCw size={14} /> Check now
                        </button>
                        <button 
                          onClick={() => handleDelete(alert.property_id)}
                          className="hover:text-red-500 transition-colors p-1" 
                          title="Remove alert"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
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
