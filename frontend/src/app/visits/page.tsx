"use client";

import { useState, useEffect } from "react";
import { MobileSidebarProvider, DashboardSidebar } from "@/components/shared/Navbar";
import { Calendar, MapPin, Clock, CheckCircle, XCircle } from "lucide-react";
import { motion } from "framer-motion";
import { useUser } from "@clerk/nextjs";
import Link from "next/link";
import Image from "next/image";

interface Visit {
  id: string;
  property_id: string;
  property_title: string;
  property_image: string;
  property_price: string;
  property_location: string;
  date: string;
  time_slot: string;
  status: string;
}

export default function VisitsPage() {
  const { user } = useUser();
  const userEmail = user?.primaryEmailAddress?.emailAddress;
  const [visits, setVisits] = useState<Visit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (userEmail) {
      fetchVisits();
    }
  }, [userEmail]);

  const fetchVisits = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/visits/?user_email=${encodeURIComponent(userEmail!)}`);
      const json = await res.json();
      if (json.data) {
        setVisits(json.data);
      }
    } catch (err) {
      console.error("Failed to fetch visits", err);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (visitId: string) => {
    if (!confirm("Are you sure you want to cancel this visit?")) return;
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/visits/${visitId}`, {
        method: "DELETE"
      });
      fetchVisits();
    } catch (err) {
      console.error(err);
    }
  };

  const formatPrice = (price: string | number) => {
    if (!price) return "N/A";
    const p = typeof price === "string" ? parseFloat(price.replace(/[^\d.]/g, '')) : price;
    if (isNaN(p)) return price;
    return p >= 100 ? `₹${(p / 100).toFixed(2)} Cr` : `₹${p} L`;
  };

  return (
    <MobileSidebarProvider>
      <div className="min-h-screen bg-cream flex font-sans">
        <DashboardSidebar />
        
        <main className="flex-1 lg:pl-64 flex flex-col">
          {/* Header */}
          <header className="sticky top-0 z-30 bg-cream/80 backdrop-blur-md border-b border-border-custom px-4 lg:px-8 py-4 flex items-center justify-between">
            <div>
              <h1 className="font-playfair text-2xl lg:text-3xl text-charcoal flex items-center gap-2">
                <Calendar className="w-6 h-6 text-forest" />
                Scheduled Visits
              </h1>
              <p className="text-muted font-dm mt-1">Manage your upcoming property tours.</p>
            </div>
          </header>

          <div className="p-4 lg:p-8 flex-1">
            {loading ? (
              <div className="flex justify-center items-center h-40">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-forest"></div>
              </div>
            ) : visits.length === 0 ? (
              <div className="text-center py-20 bg-surface border border-border-custom rounded-2xl max-w-2xl mx-auto">
                <Calendar className="w-12 h-12 text-muted mx-auto mb-4" />
                <h3 className="text-xl font-playfair text-charcoal mb-2">No visits scheduled</h3>
                <p className="text-muted font-dm mb-6">You haven&apos;t scheduled any property tours yet.</p>
                <Link href="/" className="px-6 py-2 bg-forest text-cream rounded-lg font-dm font-semibold hover:bg-forest/90 transition-colors">
                  Explore Properties
                </Link>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {visits.map((visit, idx) => {
                  const dateObj = new Date(visit.date);
                  const formattedDate = dateObj.toLocaleDateString("en-US", { weekday: 'short', month: 'short', day: 'numeric' });
                  
                  return (
                    <motion.div 
                      key={visit.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.05 }}
                      className="bg-surface border border-border-custom rounded-2xl overflow-hidden hover:shadow-lg transition-all"
                    >
                      {/* Image */}
                      <Link href={`/property/${visit.property_id}`} className="block relative h-48 w-full group overflow-hidden">
                        {visit.property_image ? (
                          <Image src={visit.property_image} alt={visit.property_title} fill className="object-cover group-hover:scale-105 transition-transform duration-500" />
                        ) : (
                          <div className="w-full h-full bg-border-custom flex items-center justify-center text-muted">No Image</div>
                        )}
                        <div className="absolute top-3 right-3">
                          <span className={`px-3 py-1 rounded-full text-xs font-dm font-bold shadow-md ${
                            visit.status === "scheduled" ? "bg-forest text-white" :
                            visit.status === "completed" ? "bg-charcoal text-white" :
                            "bg-danger text-white"
                          }`}>
                            {visit.status.charAt(0).toUpperCase() + visit.status.slice(1)}
                          </span>
                        </div>
                      </Link>

                      {/* Content */}
                      <div className="p-5">
                        <h3 className="font-dm font-bold text-charcoal text-lg mb-1 truncate">{visit.property_title}</h3>
                        <p className="text-sm text-muted flex items-center gap-1 mb-4">
                          <MapPin className="w-3.5 h-3.5" />
                          {visit.property_location}
                        </p>

                        <div className="bg-cream rounded-xl p-3 mb-4 border border-border-custom flex flex-col gap-2">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-forest/10 flex items-center justify-center text-forest">
                              <Calendar className="w-4 h-4" />
                            </div>
                            <div>
                              <p className="text-xs font-dm text-muted uppercase tracking-wider mb-0.5">Date</p>
                              <p className="text-sm font-dm font-bold text-charcoal">{formattedDate}</p>
                            </div>
                          </div>
                          <div className="w-full h-px bg-border-custom"></div>
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-warm-gold/20 flex items-center justify-center text-warm-gold">
                              <Clock className="w-4 h-4" />
                            </div>
                            <div>
                              <p className="text-xs font-dm text-muted uppercase tracking-wider mb-0.5">Time</p>
                              <p className="text-sm font-dm font-bold text-charcoal">{visit.time_slot}</p>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center justify-between mt-5">
                          <span className="font-playfair text-xl font-bold text-forest">
                            {formatPrice(visit.property_price)}
                          </span>
                          
                          {visit.status === "scheduled" && (
                            <button 
                              onClick={() => handleCancel(visit.id)}
                              className="text-sm font-dm font-semibold text-danger hover:underline flex items-center gap-1"
                            >
                              Cancel
                            </button>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            )}
          </div>
        </main>
      </div>
    </MobileSidebarProvider>
  );
}
