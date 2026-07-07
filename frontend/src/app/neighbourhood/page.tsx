"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, MapPin, Search, Sparkles, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { formatPrice } from "@/lib/utils";
import { STATIC_IMAGES } from "@/lib/unsplash";

interface Property {
  id: string;
  title: string;
  apartmentName?: string;
  locality: string;
  city: string;
  bhk: string;
  price: number;
  images: string[];
}

function resolveId(raw: any, index: number): string {
  const direct = raw?.id ?? raw?._id;
  if (typeof direct === "string") return direct;
  if (direct && typeof direct === "object" && typeof direct.$oid === "string") return direct.$oid;
  if (typeof raw?.external_id === "string") return raw.external_id;
  return `prop-${index}`;
}

function normalizeProperty(raw: any, index: number): Property {
  const images = Array.isArray(raw?.images) && raw.images.length > 0
    ? raw.images
    : [STATIC_IMAGES.apartment1];

  let apartmentName = raw?.apartment_name || raw?.apartmentName;
  if (typeof apartmentName === "string" && apartmentName.trim().length > 2) {
    apartmentName = apartmentName.trim().replace(/^(?:in|at|near|of)\s+/i, "").split(",")[0].trim();
  } else {
    apartmentName = undefined;
  }

  const rawTitle = typeof raw?.title === "string" ? raw.title.trim() : "";
  let title = rawTitle;
  if (rawTitle && /(verified|flat|flats|rent|sale|properties|apartments|listings|is available|price range)/i.test(rawTitle)) {
    title = apartmentName || raw?.locality || "Property";
  }

  return {
    id: resolveId(raw, index),
    title: apartmentName || title || "Property",
    apartmentName,
    locality: raw?.locality || raw?.city || "Unknown locality",
    city: raw?.city || "Unknown city",
    bhk: typeof raw?.bhk === "string" ? raw.bhk : String(raw?.bhk || "N/A"),
    price: Number(raw?.price || 0),
    images,
  };
}

export default function NeighbourhoodDashboardIndex() {
  const router = useRouter();
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    let isMounted = true;
    
    async function fetchProperties() {
      try {
        setLoading(true);
        const res = await fetch("http://localhost:10000/api/properties/");
        const json = await res.json();
        
        if (isMounted && Array.isArray(json?.data)) {
          setProperties(json.data.map(normalizeProperty));
        }
      } catch (err) {
        console.error("Failed to fetch properties for neighbourhood dashboard:", err);
        if (isMounted) setError("Failed to load properties. Please try again.");
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    
    fetchProperties();
    return () => { isMounted = false; };
  }, []);

  const filteredProperties = useMemo(() => {
    if (!searchQuery.trim()) return properties;
    const query = searchQuery.toLowerCase();
    return properties.filter(p => 
      p.title.toLowerCase().includes(query) ||
      p.locality.toLowerCase().includes(query) ||
      p.city.toLowerCase().includes(query) ||
      p.bhk.toLowerCase().includes(query)
    );
  }, [properties, searchQuery]);

  return (
    <div className="min-h-screen bg-dark-bg text-white flex flex-col font-dm selection:bg-warm-gold/30">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-8 py-5">
        <Link href="/dashboard" className="flex items-center gap-2 text-muted hover:text-white transition-colors text-sm">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </Link>
        <Link href="/" className="flex items-center gap-1">
          <span className="font-playfair italic text-xl text-white">griha</span>
          <span className="font-playfair text-xl text-warm-gold font-bold">AI</span>
        </Link>
        <div className="w-[140px]"></div> {/* Spacer to keep logo centered */}
      </div>

      {/* Hero Section */}
      <div className="flex flex-col items-center justify-center mt-12 mb-16 px-6 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-warm-gold/40 bg-warm-gold/5 text-warm-gold text-xs font-semibold tracking-wide mb-6">
          <MapPin className="w-3.5 h-3.5" /> AI Neighbourhood Explorer
        </div>
        
        <h1 className="font-playfair text-5xl md:text-6xl text-white mb-6">
          Explore Your <span className="text-warm-gold">Neighbourhood</span>
        </h1>
        
        <p className="text-dark-text max-w-lg mx-auto text-base leading-relaxed mb-10">
          Select a property you searched. Ask AI anything — hospitals nearby, distance to a place, parks, supermarkets.
        </p>

        {/* Search Bar */}
        <div className="relative w-full max-w-2xl">
          <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-dark-icon" />
          <input 
            id="neighbourhood-search"
            name="neighbourhood-search"
            type="text" 
            placeholder="Filter by locality, BHK.."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-dark-card border border-dark-border rounded-full py-4 pl-14 pr-6 text-white placeholder-dark-icon focus:outline-none focus:border-warm-gold/50 transition-colors shadow-lg"
          />
        </div>
      </div>

      {/* Grid Section */}
      <div className="flex-1 px-8 pb-20 max-w-7xl mx-auto w-full">
        {loading ? (
          <div className="flex justify-center items-center py-20">
            <Loader2 className="w-10 h-10 text-warm-gold animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-20 text-danger">{error}</div>
        ) : filteredProperties.length === 0 ? (
          <div className="text-center py-20 text-dark-icon">
            No properties found matching "{searchQuery}"
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProperties.map((property, i) => (
              <motion.div
                key={property.id}
                onClick={() => router.push(`/neighbourhood/${property.id}`)}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05, duration: 0.4 }}
                className="bg-dark-card border border-dark-border rounded-2xl overflow-hidden hover:border-warm-gold/30 transition-colors group cursor-pointer"
              >
                {/* Image Area */}
                <div className="relative h-[220px] w-full overflow-hidden bg-dark-img">
                  <img 
                    src={property.images[0]} 
                    alt={property.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                  />
                  <div className="absolute top-4 left-4 bg-forest text-white text-xs font-bold px-3 py-1.5 rounded-full shadow-sm">
                    {property.bhk}
                  </div>
                </div>

                {/* Card Content */}
                <div className="p-5">
                  <h3 className="text-lg font-bold text-white truncate mb-2">
                    {property.title}
                  </h3>
                  <div className="flex items-center gap-1.5 text-sm text-dark-text mb-6">
                    <MapPin className="w-4 h-4 shrink-0" />
                    <span className="truncate">{property.locality}, {property.city}</span>
                  </div>
                  
                  <div className="flex items-center justify-between mt-auto">
                    <span className="text-success font-bold">
                      {formatPrice(property.price)}/mo
                    </span>
                    <Link 
                      href={`/neighbourhood/${property.id}`}
                      className="text-warm-gold text-sm font-semibold flex items-center gap-1.5 hover:underline"
                    >
                      <MapPin className="w-4 h-4" /> Explore &rarr;
                    </Link>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Floating Action Button */}
      <button className="fixed bottom-8 right-8 w-14 h-14 bg-forest text-white rounded-full shadow-xl flex items-center justify-center hover:bg-forest-light transition-transform hover:scale-105">
        <Sparkles className="w-6 h-6" />
      </button>
    </div>
  );
}
