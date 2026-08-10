"use client";

import { useState, useEffect } from "react";
import { MobileSidebarProvider } from "@/components/shared/Navbar";
import { DashboardSidebar } from "@/components/shared/Navbar";
import { Map, TrendingUp, Search, Info } from "lucide-react";
import { formatPrice } from "@/lib/utils";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from "recharts";

export default function MarketHeatmapPage() {
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";
        const res = await fetch(`${apiUrl}/api/market/heatmap`);
        const json = await res.json();
        if (json.data) {
          setData(json.data);
        }
      } catch (err) {
        console.error("Failed to fetch market heatmap", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-charcoal text-white p-3 rounded-xl text-sm font-dm shadow-lg border border-border-custom">
          <p className="font-bold mb-1">{label}</p>
          <p className="text-forest-light">Avg Rent: {formatPrice(payload[0].value)}</p>
          {payload[0].payload.property_count && (
            <p className="text-muted">Listings: {payload[0].payload.property_count}</p>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <MobileSidebarProvider>
      <div className="min-h-screen bg-cream flex font-sans">
        <DashboardSidebar />
        
        <main className="flex-1 lg:pl-64 flex flex-col">
          <header className="sticky top-0 z-30 bg-cream/80 backdrop-blur-md border-b border-border-custom px-4 lg:px-8 py-4 flex items-center justify-between">
            <div>
              <h1 className="font-playfair text-2xl lg:text-3xl text-charcoal flex items-center gap-2">
                <Map className="w-6 h-6 text-forest" />
                Market Heatmap
              </h1>
              <p className="text-muted font-dm mt-1">Locality-wise rent trends and analytics.</p>
            </div>
          </header>

          <div className="p-4 lg:p-8 flex-1">
            {loading ? (
              <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-forest"></div>
              </div>
            ) : data.length === 0 ? (
              <div className="text-center py-20 bg-surface border border-border-custom rounded-2xl">
                <Search className="w-12 h-12 text-muted mx-auto mb-4" />
                <h3 className="text-xl font-playfair text-charcoal mb-2">Not enough data</h3>
                <p className="text-muted font-dm">Start scraping properties to generate market insights.</p>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="bg-surface rounded-2xl border border-border-custom p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-6">
                    <h2 className="font-dm font-bold text-lg text-charcoal flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-forest" />
                      Average Rent by Locality
                    </h2>
                    <span className="text-xs bg-forest/10 text-forest px-3 py-1 rounded-full font-semibold">
                      Based on {data.reduce((acc, curr) => acc + curr.property_count, 0)} listings
                    </span>
                  </div>
                  
                  <div className="h-[400px] w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        data={data}
                        layout="vertical"
                        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E5E0D8" />
                        <XAxis type="number" tickFormatter={(val) => `₹${val/1000}k`} stroke="#8c8577" fontSize={12} />
                        <YAxis dataKey="locality" type="category" width={120} stroke="#8c8577" fontSize={12} tick={{fill: '#1c1c1c'}} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="avg_rent" radius={[0, 4, 4, 0]} maxBarSize={32}>
                          {data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={index === 0 ? "#C9922A" : "#2D5016"} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                  {data.slice(0, 6).map((loc, idx) => (
                    <div key={idx} className="bg-surface rounded-xl border border-border-custom p-5">
                      <h3 className="font-dm font-bold text-lg text-charcoal mb-4 truncate" title={loc.locality}>{loc.locality}</h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs text-muted uppercase tracking-wider mb-1">Avg Rent</p>
                          <p className="font-playfair text-xl text-charcoal">{formatPrice(loc.avg_rent)}</p>
                        </div>
                        <div>
                          <p className="text-xs text-muted uppercase tracking-wider mb-1">Avg Size</p>
                          <p className="font-dm font-semibold text-charcoal">{loc.avg_sqft ? `${loc.avg_sqft} sqft` : "N/A"}</p>
                        </div>
                        <div className="col-span-2 pt-3 border-t border-border-custom flex items-center justify-between">
                          <span className="text-xs text-muted flex items-center gap-1"><Info className="w-3 h-3" /> Based on {loc.property_count} properties</span>
                          {loc.price_per_sqft && (
                            <span className="text-xs font-semibold text-forest">₹{loc.price_per_sqft}/sqft</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </MobileSidebarProvider>
  );
}
