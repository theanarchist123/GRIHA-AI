"use client";

import { useState, useEffect } from "react";
import { PropertyCard } from "./PropertyCard";
import { SkeletonCard } from "./LoadingState";

export function SimilarProperties({ propertyId }: { propertyId: string }) {
  const [similarProps, setSimilarProps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchSimilar() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";
        const res = await fetch(`${apiUrl}/api/properties/${propertyId}/similar?limit=3`);
        const json = await res.json();
        if (json.data) {
          setSimilarProps(json.data);
        }
      } catch (err) {
        console.error("Failed to fetch similar properties", err);
      } finally {
        setLoading(false);
      }
    }
    fetchSimilar();
  }, [propertyId]);

  if (!loading && similarProps.length === 0) {
    return null;
  }

  return (
    <div className="mt-12 mb-8">
      <h3 className="font-playfair text-2xl text-charcoal mb-6 border-b border-border-custom pb-2">
        Similar Properties You May Like
      </h3>
      
      <div className="flex gap-4 sm:gap-6 overflow-x-auto pb-6 scrollbar-thin snap-x snap-mandatory -mx-2 px-2">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={`sim-skeleton-${i}`} className="w-[280px] sm:w-[335px] shrink-0 snap-start" />
          ))
        ) : (
          similarProps.map((prop, i) => (
            <div key={prop.id || i} className="shrink-0 snap-start w-[280px] sm:w-[335px]">
              <PropertyCard property={prop} isSavedToPipeline={false} isSavedToAlerts={false} />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
