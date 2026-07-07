"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { IndianRupee, PieChart, ShieldCheck, AlertTriangle, XCircle } from "lucide-react";
import { formatPrice } from "@/lib/utils";

interface AffordabilityCalcProps {
  rentAmount: number;
  city: string;
}

export function AffordabilityCalc({ rentAmount, city }: AffordabilityCalcProps) {
  // Estimate utilities based on city (rough constants)
  const cityLower = city.toLowerCase();
  let baseUtilities = 2500;
  if (cityLower.includes("mumbai") || cityLower.includes("bengaluru") || cityLower.includes("bangalore")) {
    baseUtilities = 3500;
  } else if (cityLower.includes("delhi") || cityLower.includes("gurgaon")) {
    baseUtilities = 3000;
  }
  
  const [income, setIncome] = useState<number | "">("");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const saved = localStorage.getItem("griha_monthly_income");
    if (saved) setIncome(Number(saved));
  }, []);

  const handleIncomeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value.replace(/\D/g, "");
    const num = val ? Number(val) : "";
    setIncome(num);
    if (num) {
      localStorage.setItem("griha_monthly_income", num.toString());
    } else {
      localStorage.removeItem("griha_monthly_income");
    }
  };

  if (!mounted) return null;

  const numericIncome = typeof income === "number" ? income : 0;
  const rentPercent = numericIncome > 0 ? (rentAmount / numericIncome) * 100 : 0;
  const utilPercent = numericIncome > 0 ? (baseUtilities / numericIncome) * 100 : 0;
  const remainingAmount = Math.max(0, numericIncome - rentAmount - baseUtilities);
  const remainPercent = numericIncome > 0 ? (remainingAmount / numericIncome) * 100 : 0;

  let status = "Enter income to calculate";
  let StatusIcon = PieChart;
  let statusColor = "text-muted";
  let statusBg = "bg-surface";

  if (numericIncome > 0) {
    if (rentPercent <= 30) {
      status = "Affordable (under 30%)";
      StatusIcon = ShieldCheck;
      statusColor = "text-success";
      statusBg = "bg-success/10";
    } else if (rentPercent <= 45) {
      status = "Stretching Budget";
      StatusIcon = AlertTriangle;
      statusColor = "text-warm-gold";
      statusBg = "bg-warm-gold/10";
    } else {
      status = "Over Budget";
      StatusIcon = XCircle;
      statusColor = "text-danger";
      statusBg = "bg-danger/10";
    }
  }

  return (
    <div className="bg-surface rounded-2xl border border-border-custom p-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-dm font-bold text-charcoal text-lg flex items-center gap-2">
          <PieChart className="w-5 h-5 text-forest" />
          Affordability Calculator
        </h3>
        {numericIncome > 0 && (
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${statusBg} ${statusColor}`}>
            <StatusIcon className="w-3.5 h-3.5" />
            {status}
          </span>
        )}
      </div>

      <div className="mb-6">
        <label className="block text-xs font-dm font-semibold text-muted mb-2">Your Monthly Income (Take-home)</label>
        <div className="relative">
          <IndianRupee className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
          <input
            id="monthly-income"
            name="monthly-income"
            type="text"
            value={income ? income.toLocaleString("en-IN") : ""}
            onChange={handleIncomeChange}
            placeholder="e.g. 1,00,000"
            className="w-full pl-9 pr-4 py-2.5 bg-cream border border-border-custom rounded-xl text-sm font-dm focus:outline-none focus:border-forest transition-colors"
          />
        </div>
      </div>

      {numericIncome > 0 && (
        <div className="space-y-4">
          <div className="h-2.5 w-full bg-cream rounded-full flex overflow-hidden">
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(100, rentPercent)}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className={`h-full ${rentPercent > 45 ? "bg-danger" : rentPercent > 30 ? "bg-warm-gold" : "bg-forest"}`}
            />
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(100 - rentPercent, utilPercent)}%` }}
              transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
              className="h-full bg-charcoal/40"
            />
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: `${remainPercent}%` }}
              transition={{ duration: 0.5, delay: 0.4, ease: "easeOut" }}
              className="h-full bg-success/60"
            />
          </div>

          <div className="grid grid-cols-3 gap-2 pt-2">
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <div className={`w-2 h-2 rounded-full ${rentPercent > 45 ? "bg-danger" : rentPercent > 30 ? "bg-warm-gold" : "bg-forest"}`} />
                <span className="text-[10px] font-dm text-muted">Rent ({rentPercent.toFixed(0)}%)</span>
              </div>
              <p className="text-xs font-dm font-semibold text-charcoal">{formatPrice(rentAmount)}</p>
            </div>
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-2 h-2 rounded-full bg-charcoal/40" />
                <span className="text-[10px] font-dm text-muted">Utilities</span>
              </div>
              <p className="text-xs font-dm font-semibold text-charcoal">{formatPrice(baseUtilities)}</p>
            </div>
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-2 h-2 rounded-full bg-success/60" />
                <span className="text-[10px] font-dm text-muted">Remaining</span>
              </div>
              <p className="text-xs font-dm font-semibold text-charcoal">{formatPrice(remainingAmount)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
