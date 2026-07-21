"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";

// Dynamic import with SSR disabled is required for react-leaflet
const MapInner = dynamic(() => import("./MapInner"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[300px] flex items-center justify-center bg-cream/50 rounded-2xl border border-border-custom">
      <Loader2 className="w-6 h-6 animate-spin text-forest" />
      <span className="ml-2 text-sm font-dm text-muted">Loading map...</span>
    </div>
  ),
});

interface PropertyMapProps {
  propertyId: string;
  onMarkerClick: (name: string) => void;
}

export function PropertyMap({ propertyId, onMarkerClick }: PropertyMapProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchMapData() {
      if (!propertyId) return;
      try {
        setLoading(true);
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/neighbourhood/amenities/${propertyId}`);
        const json = await res.json();
        
        if (json.status === "success") {
          setData(json.data);
        } else {
          setError(json.message || "Failed to load map data");
        }
      } catch (err) {
        setError("Network error loading map");
      } finally {
        setLoading(false);
      }
    }

    fetchMapData();
  }, [propertyId]);

  if (error) {
    return (
      <div className="w-full p-6 text-center bg-danger/10 border border-danger/20 rounded-2xl">
        <p className="text-sm font-dm text-danger">{error}</p>
      </div>
    );
  }

  if (loading || !data) {
    return (
      <div className="w-full h-[400px] flex items-center justify-center bg-cream/50 rounded-2xl border border-border-custom">
        <Loader2 className="w-6 h-6 animate-spin text-forest" />
      </div>
    );
  }

  return (
    <div className="w-full h-[400px] rounded-2xl overflow-hidden border border-border-custom shadow-sm relative z-0">
      <MapInner 
        center={data.center} 
        markers={data.markers} 
        onMarkerClick={onMarkerClick} 
      />
    </div>
  );
}
