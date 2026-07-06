"use client";

import { useState } from "react";
import { Map, Car, Train, Loader2, ArrowRight } from "lucide-react";

interface CommuteCalcProps {
  propertyAddress: string;
  propertyCity: string;
}

export function CommuteCalc({ propertyAddress, propertyCity }: CommuteCalcProps) {
  const [destination, setDestination] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const calculateCommute = async () => {
    if (!destination.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const fullOrigin = `${propertyAddress}, ${propertyCity}`;
      const fullDest = `${destination}, ${propertyCity}`; // Assume same city for better geocoding accuracy
      
      const res = await fetch(`http://localhost:10000/api/properties/commute/calculate?origin=${encodeURIComponent(fullOrigin)}&destination=${encodeURIComponent(fullDest)}`);
      const json = await res.json();
      
      if (json.status === "success") {
        setResult(json.data);
      } else {
        setError(json.message || "Could not calculate commute.");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-surface rounded-2xl border border-border-custom p-6">
      <h3 className="font-dm font-bold text-charcoal text-lg mb-5 flex items-center gap-2">
        <Map className="w-5 h-5 text-forest" />
        Commute Calculator
      </h3>
      
      <div className="mb-5">
        <label className="block text-xs font-dm font-semibold text-muted mb-2">Workplace or Frequent Destination</label>
        <div className="flex gap-3">
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && calculateCommute()}
            placeholder="e.g. Cyber City or MG Road"
            className="flex-1 px-4 py-2.5 bg-cream border border-border-custom rounded-xl text-sm font-dm focus:outline-none focus:border-forest"
          />
          <button 
            onClick={calculateCommute}
            disabled={loading || !destination.trim()}
            className="px-5 py-2.5 bg-charcoal text-cream font-dm font-semibold rounded-xl hover:bg-charcoal/90 transition-colors disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Calculate"}
          </button>
        </div>
        {error && <p className="text-xs text-danger font-dm mt-2">{error}</p>}
      </div>

      {result && (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-cream rounded-xl p-4 border border-border-custom">
            <div className="flex items-center gap-2 mb-2 text-charcoal">
              <Car className="w-4 h-4" />
              <span className="text-sm font-dm font-bold">Driving</span>
            </div>
            <p className="text-2xl font-playfair text-forest">{result.driving.duration_mins} min</p>
            <p className="text-xs font-dm text-muted mt-1">{result.driving.distance_km} km away</p>
          </div>
          
          <div className="bg-cream rounded-xl p-4 border border-border-custom">
            <div className="flex items-center gap-2 mb-2 text-charcoal">
              <Train className="w-4 h-4" />
              <span className="text-sm font-dm font-bold">Transit</span>
            </div>
            <p className="text-2xl font-playfair text-forest">{result.transit.duration_mins} min</p>
            <p className="text-xs font-dm text-muted mt-1">Includes approx. walking time</p>
          </div>
        </div>
      )}
    </div>
  );
}
