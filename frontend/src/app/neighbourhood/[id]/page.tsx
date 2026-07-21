"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowLeft, Loader2, MapPin } from "lucide-react";
import dynamic from "next/dynamic";
import NeighbourhoodChat from "@/components/shared/NeighbourhoodChat";

// Dynamically import map so Leaflet doesn't run on the server
const MapComponent = dynamic(
  () => import("@/components/shared/MapComponent"),
  { ssr: false, loading: () => <div className="w-full h-full bg-cream animate-pulse rounded-2xl" /> }
);

interface PointOfInterest {
  name: string;
  lat: number;
  lng: number;
  distance_m: number;
  tags?: Record<string, string>;
}

interface MapState {
  center: { lat: number; lng: number; address: string } | null;
  markers: PointOfInterest[];
}

export default function NeighbourhoodPage() {
  const params = useParams();
  const router = useRouter();
  const propertyId = typeof params?.id === "string" ? params.id : "";

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [mapState, setMapState] = useState<MapState>({
    center: null,
    markers: []
  });

  useEffect(() => {
    if (!propertyId) return;
    
    // Initial fetch to get the property details and trigger geocoding
    async function initProperty() {
      setLoading(true);
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/properties/${propertyId}`);
        const json = await res.json();
        
        if (json.status === "success" && json.data) {
          const prop = json.data;
          const address = prop.address || `${prop.locality}, ${prop.city}`;
          
          // Send an initial hidden chat query to just get coordinates
          const geoRes = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/neighbourhood/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ property_id: propertyId, query: "where is this exactly?" })
          });
          const geoData = await geoRes.json();
          
          if (geoData.status === "success" && geoData.data.property_center) {
            setMapState({
              center: geoData.data.property_center,
              markers: []
            });
          }
        } else {
          setError("Property not found");
        }
      } catch (err) {
        setError("Failed to connect to server. Is the backend running?");
      } finally {
        setLoading(false);
      }
    }
    
    initProperty();
  }, [propertyId]);

  const handleUpdateMap = (center: any, markers: PointOfInterest[]) => {
    setMapState({ center, markers });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-dark-bg flex items-center justify-center">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center space-y-4">
          <Loader2 className="w-10 h-10 text-warm-gold animate-spin mx-auto" />
          <p className="font-dm text-white text-lg">Initializing Neighbourhood Map...</p>
        </motion.div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-dark-bg p-6 flex flex-col items-center justify-center">
        <p className="text-white font-dm text-lg">{error}</p>
        <button onClick={() => router.back()} className="text-warm-gold underline text-sm font-dm mt-3 inline-block">Go Back</button>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-dark-bg overflow-hidden selection:bg-warm-gold/30">
      {/* Top bar */}
      <div className="shrink-0 bg-dark-bg border-b border-dark-border px-6 py-3">
        <div className="flex items-center justify-between max-w-full mx-auto">
          <button onClick={() => router.back()} className="flex items-center gap-2 text-dark-text hover:text-white transition-colors">
            <ArrowLeft className="w-5 h-5" /><span className="text-sm font-dm">Back to Dashboard</span>
          </button>
          <Link href="/" className="flex items-center gap-1">
            <span className="font-playfair italic text-lg text-white">griha</span>
            <span className="font-playfair text-lg text-warm-gold font-bold">AI</span>
          </Link>
        </div>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 p-6 min-h-0">
        
        {/* Left Pane - Map */}
        <div className="lg:col-span-2 h-[50vh] lg:h-full relative rounded-2xl overflow-hidden shadow-sm border border-dark-border">
          {mapState.center ? (
            <MapComponent center={mapState.center} markers={mapState.markers} />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-dark-card border border-dark-border">
              <Loader2 className="w-8 h-8 text-warm-gold animate-spin" />
            </div>
          )}
          
          <div className="absolute top-4 left-4 z-[400] bg-dark-bg/90 backdrop-blur-md px-4 py-2 rounded-xl border border-dark-border shadow-lg">
            <div className="flex items-center gap-2 text-sm font-dm text-white">
              <MapPin className="w-4 h-4 text-warm-gold" />
              <span className="font-semibold truncate max-w-xs">{mapState.center?.address || "Loading location..."}</span>
            </div>
          </div>
        </div>

        {/* Right Pane - Chat */}
        <div className="lg:col-span-1 h-[50vh] lg:h-full">
          <NeighbourhoodChat propertyId={propertyId} onUpdateMap={handleUpdateMap} />
        </div>
      </div>
    </div>
  );
}
