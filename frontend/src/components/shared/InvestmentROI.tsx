"use client";

import { useState, useEffect } from "react";
import { TrendingUp, Activity, PieChart, Info } from "lucide-react";
import { motion } from "framer-motion";
import { formatPrice } from "@/lib/utils";

interface InvestmentROIProps {
  propertyId: string;
}

export function InvestmentROI({ propertyId }: InvestmentROIProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";
        const res = await fetch(`${apiUrl}/api/properties/${propertyId}/investment`);
        const json = await res.json();
        if (json.data) {
          setData(json.data);
        }
      } catch (err) {
        console.error("Failed to fetch investment analytics", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [propertyId]);

  if (loading) {
    return (
      <div className="bg-surface rounded-2xl border border-border-custom p-6 animate-pulse">
        <div className="h-6 w-48 bg-cream rounded-md mb-4"></div>
        <div className="h-32 bg-cream rounded-md mb-4"></div>
        <div className="flex gap-4">
          <div className="flex-1 h-16 bg-cream rounded-md"></div>
          <div className="flex-1 h-16 bg-cream rounded-md"></div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-surface rounded-2xl border border-border-custom overflow-hidden"
    >
      <div className="p-6 border-b border-border-custom flex items-center justify-between">
        <h2 className="font-playfair text-2xl text-charcoal flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-forest" />
          Investment & ROI Analysis
        </h2>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-cream rounded-xl p-4 border border-border-custom">
            <p className="text-xs font-dm font-semibold text-muted uppercase tracking-wider mb-1 flex items-center gap-1">
              Estimated Value <Info className="w-3 h-3 text-muted/60" />
            </p>
            <p className="font-playfair text-2xl text-charcoal">{formatPrice(data.estimated_value)}</p>
            <p className="text-xs text-muted mt-1">Based on 3% avg rental yield</p>
          </div>
          <div className="bg-forest/5 rounded-xl p-4 border border-forest/10">
            <p className="text-xs font-dm font-semibold text-forest uppercase tracking-wider mb-1 flex items-center gap-1">
              Annual ROI Projection <Activity className="w-3 h-3 text-forest/60" />
            </p>
            <p className="font-dm font-bold text-2xl text-forest">{data.rental_yield + data.annual_appreciation}%</p>
            <p className="text-xs text-forest-light mt-1">Rental ({data.rental_yield}%) + Appreciation ({data.annual_appreciation}%)</p>
          </div>
        </div>

        <div>
          <h3 className="font-dm font-bold text-sm text-charcoal mb-4 flex items-center gap-2">
            <PieChart className="w-4 h-4 text-muted" />
            5-Year Value & Cashflow Projection
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border-custom">
                  <th className="py-2 text-xs font-dm font-semibold text-muted">Year</th>
                  <th className="py-2 text-xs font-dm font-semibold text-muted">Estimated Prop. Value</th>
                  <th className="py-2 text-xs font-dm font-semibold text-muted text-right">Annual Rent Income</th>
                </tr>
              </thead>
              <tbody>
                {data.projections.map((p: any, idx: number) => (
                  <tr key={idx} className="border-b border-border-custom/50 last:border-0 hover:bg-cream/50 transition-colors">
                    <td className="py-3 text-sm font-dm font-medium text-charcoal">{p.year}</td>
                    <td className="py-3 text-sm font-dm text-muted">{formatPrice(p.property_value)}</td>
                    <td className="py-3 text-sm font-dm font-bold text-forest text-right">+{formatPrice(p.annual_rent)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </motion.section>
  );
}
