"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Receipt, Info, ShieldCheck, Wallet, ArrowRight } from "lucide-react";
import Link from "next/link";
import { formatPrice } from "@/lib/utils";

interface MoveInCostProps {
  propertyId: string;
}

interface CostBreakdown {
  label: string;
  value: number;
  type: string;
}

interface CostData {
  breakdown: CostBreakdown[];
  total: number;
  deposit: number;
  fees: number;
  advance_rent: number;
}

export function MoveInCostBreakdown({ propertyId }: MoveInCostProps) {
  const [data, setData] = useState<CostData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/properties/${propertyId}/move-in-cost`)
      .then(res => res.json())
      .then(json => {
        if (json.status === "success") {
          setData(json.data);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to fetch move-in cost", err);
        setLoading(false);
      });
  }, [propertyId]);

  if (loading) {
    return (
      <div className="bg-surface rounded-2xl border border-border-custom p-6 animate-pulse">
        <div className="h-6 w-1/3 bg-cream rounded mb-4"></div>
        <div className="h-4 w-full bg-cream rounded mb-2"></div>
        <div className="h-4 w-2/3 bg-cream rounded"></div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="bg-surface rounded-2xl border border-border-custom p-6">
      <h3 className="font-dm font-bold text-charcoal text-lg mb-5 flex items-center gap-2">
        <Wallet className="w-5 h-5 text-forest" />
        Total Move-in Estimate
      </h3>
      
      <div className="flex flex-col md:flex-row items-center gap-6 mb-6">
        <div className="w-full md:w-1/3 text-center md:text-left border-b md:border-b-0 md:border-r border-border-custom pb-4 md:pb-0 md:pr-6">
          <p className="text-xs text-muted font-dm uppercase tracking-wider mb-1">Estimated Outflow</p>
          <p className="text-3xl font-playfair text-forest mb-1">{formatPrice(data.total)}</p>
          <p className="text-xs text-muted font-dm">To be paid before move-in</p>
        </div>
        
        <div className="w-full md:w-2/3 grid grid-cols-2 gap-4">
          <div className="bg-cream rounded-xl p-3 border border-border-custom">
            <div className="flex items-center gap-1.5 mb-1 text-success">
              <ShieldCheck className="w-4 h-4" />
              <span className="text-xs font-dm font-bold">Refundable</span>
            </div>
            <p className="text-lg font-dm font-semibold text-charcoal">{formatPrice(data.deposit)}</p>
          </div>
          <div className="bg-cream rounded-xl p-3 border border-border-custom">
            <div className="flex items-center gap-1.5 mb-1 text-warm-gold">
              <Receipt className="w-4 h-4" />
              <span className="text-xs font-dm font-bold">One-time Fees</span>
            </div>
            <p className="text-lg font-dm font-semibold text-charcoal">{formatPrice(data.fees)}</p>
          </div>
        </div>
      </div>

      <div>
        <h4 className="text-sm font-dm font-semibold text-charcoal mb-3 flex items-center gap-1.5">
          Breakdown <Info className="w-3.5 h-3.5 text-muted" />
        </h4>
        <div className="space-y-2">
          {data.breakdown.map((item, idx) => (
            <div key={idx} className="flex justify-between items-center py-2 border-b border-border-custom last:border-0">
              <span className="text-sm font-dm text-muted">{item.label}</span>
              <span className="text-sm font-dm font-semibold text-charcoal">{formatPrice(item.value)}</span>
            </div>
          ))}
        </div>
      </div>
      
      <Link 
        href={`/negotiate/${propertyId}`}
        className="w-full mt-6 py-3 bg-forest/10 hover:bg-forest/20 text-forest font-dm font-bold rounded-xl transition-colors flex items-center justify-center gap-2"
      >
        Negotiate these terms <ArrowRight className="w-4 h-4" />
      </Link>
    </div>
  );
}
