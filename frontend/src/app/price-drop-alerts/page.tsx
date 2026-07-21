"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { DashboardSidebar, DashboardTopBar } from "@/components/shared/Navbar";
import { MapPin, Star, ChevronDown, RefreshCw, Trash2, Sparkles, TrendingDown, Bell } from "lucide-react";
import { useUser } from "@clerk/nextjs";

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
  const { user, isLoaded } = useUser();
  
  const userEmail = user?.primaryEmailAddress?.emailAddress;

  useEffect(() => {
    if (isLoaded) {
        fetchAlerts();
    }
  }, [isLoaded, userEmail]);

  const fetchAlerts = async () => {
    if (!userEmail) {
        setLoading(false);
        return;
    }
    setLoading(true);
    try {
      let res;
      let retryCount = 0;
      while (retryCount < 3) {
        try {
          res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/alerts/?user_email=${encodeURIComponent(userEmail)}`);
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
    if (!userEmail) return;
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/alerts/${property_id}?user_email=${encodeURIComponent(userEmail)}`, {
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
          <div className="flex items-center justify-between w-full">
            <div>
              <h1 className="text-3xl font-playfair text-charcoal flex items-center gap-3">
                Price Drop Alerts
              </h1>
              <p className="text-muted text-sm font-dm mt-1">
                {alerts.filter(a => a.status !== "triggered").length} watching · {alerts.filter(a => a.status === "triggered").length} triggered
              </p>
            </div>
            <button onClick={fetchAlerts} className="px-4 py-2 border border-border-custom rounded-xl font-dm text-sm font-bold flex items-center gap-2 hover:bg-cream transition-colors">
              <RefreshCw size={14} /> Check All Prices
            </button>
          </div>
        </header>

        {/* Stats Row */}
        <div className="px-6 py-4 flex gap-4 border-b border-border-custom bg-surface">
            <div className="flex-1 bg-warm-gold/10 p-4 rounded-xl flex items-center gap-4">
                <div className="p-3 bg-white rounded-full shadow-sm text-warm-gold">
                    <Bell size={20} />
                </div>
                <div>
                    <p className="text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Active Alerts</p>
                    <p className="text-2xl font-bold text-warm-gold">{alerts.filter(a => a.status !== "triggered").length}</p>
                </div>
            </div>
            <div className="flex-1 bg-forest/10 p-4 rounded-xl flex items-center gap-4">
                <div className="p-3 bg-white rounded-full shadow-sm text-forest">
                    <TrendingDown size={20} />
                </div>
                <div>
                    <p className="text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Potential Savings</p>
                    <p className="text-2xl font-bold text-forest">
                      ₹{alerts.reduce((acc, curr) => {
                          const save = parseFloat(curr.saveAmount.replace(/[^\d.]/g, ''));
                          return acc + (isNaN(save) ? 0 : save);
                      }, 0).toFixed(1)} {alerts.length > 0 && alerts[0].saveAmount.includes("Cr") ? "Cr" : "L"}
                    </p>
                </div>
            </div>
            <div className="flex-1 bg-charcoal/5 p-4 rounded-xl flex items-center gap-4">
                <div className="p-3 bg-white rounded-full shadow-sm text-charcoal">
                    <Star size={20} />
                </div>
                <div>
                    <p className="text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Triggered</p>
                    <p className="text-2xl font-bold text-charcoal">{alerts.filter(a => a.status === "triggered").length}</p>
                </div>
            </div>
        </div>

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
                    <div className={`px-4 py-2 border-t flex items-center justify-between ${alert.status === "triggered" ? "bg-green-50 border-forest/20" : "bg-surface/50 border-border-custom"}`}>
                      <div className="flex items-center gap-2">
                        {alert.status === "triggered" ? (
                          <>
                            <TrendingDown size={14} className="text-forest" />
                            <span className="text-xs font-bold text-forest font-dm uppercase tracking-wider">Triggered</span>
                          </>
                        ) : (
                          <>
                            <span className="text-warm-gold text-xs">→</span>
                            <span className="text-xs font-bold text-muted font-dm uppercase tracking-wider">Stable</span>
                          </>
                        )}
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
