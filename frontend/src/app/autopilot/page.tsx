"use client";

import { useState, useEffect } from "react";
import { MobileSidebarProvider, DashboardSidebar } from "@/components/shared/Navbar";
import { Bot, Play, Pause, Trash2, Plus, CheckCircle, AlertTriangle, Clock, Zap, MapPin, Settings } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useUser } from "@clerk/nextjs";
import Link from "next/link";
import { formatPrice } from "@/lib/utils";

interface AutopilotMatch {
  property_id: string;
  match_score: number;
  found_at: string;
  legal_checked: boolean;
  legal_status: string | null;
}

interface AutopilotRun {
  run_id: string;
  started_at: string;
  completed_at: string | null;
  properties_scraped: number;
  new_matches: number;
  legal_checks_run: number;
  status: string;
  error: string | null;
}

interface HuntData {
  id: string;
  status: string;
  locations: string[];
  bhk: string;
  max_budget: number;
  min_budget: number;
  total_properties_found: number;
  matches: AutopilotMatch[];
  runs?: AutopilotRun[];
}

export default function AutopilotPage() {
  const { user } = useUser();
  const clerkId = user?.id;
  const userEmail = user?.primaryEmailAddress?.emailAddress;
  
  const [hunt, setHunt] = useState<HuntData | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Create form state
  const [formLocations, setFormLocations] = useState("");
  const [formBhk, setFormBhk] = useState("2 BHK");
  const [formMinBudget, setFormMinBudget] = useState(10000);
  const [formMaxBudget, setFormMaxBudget] = useState(50000);
  const [formAutoLegal, setFormAutoLegal] = useState(true);

  // Autocomplete state
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isFetchingSuggestions, setIsFetchingSuggestions] = useState(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";

  useEffect(() => {
    if (clerkId) fetchHunt();
  }, [clerkId]);

  async function fetchHunt() {
    try {
      const res = await fetch(`${apiUrl}/api/autopilot/${clerkId}`);
      const json = await res.json();
      if (json.status === "success" && json.data) {
        setHunt(json.data);
      } else {
        setHunt(null);
      }
    } catch (err) {
      console.error("Failed to fetch autopilot hunt", err);
    } finally {
      setLoading(false);
    }
  }

  async function createHunt() {
    if (!clerkId) return;
    setCreating(true);
    try {
      const locations = formLocations.split(",").map(l => l.trim()).filter(Boolean);
      const res = await fetch(`${apiUrl}/api/autopilot/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          clerk_id: clerkId,
          locations,
          bhk: formBhk,
          min_budget: formMinBudget,
          max_budget: formMaxBudget,
          auto_legal_check: formAutoLegal,
          digest_email: userEmail || null,
        }),
      });
      const json = await res.json();
      if (json.data) {
        setHunt(json.data);
        setShowCreateForm(false);
      }
    } catch (err) {
      console.error("Failed to create hunt", err);
    } finally {
      setCreating(false);
    }
  }

  async function toggleHunt() {
    if (!hunt) return;
    try {
      const res = await fetch(`${apiUrl}/api/autopilot/${hunt.id}/toggle`, { method: "PATCH" });
      const json = await res.json();
      if (json.data) setHunt(json.data);
    } catch (err) {
      console.error(err);
    }
  }

  async function deleteHunt() {
    if (!hunt || !confirm("Are you sure you want to stop this autopilot hunt?")) return;
    try {
      await fetch(`${apiUrl}/api/autopilot/${hunt.id}`, { method: "DELETE" });
      setHunt(null);
    } catch (err) {
      console.error(err);
    }
  }

  const statusColor = (status: string) => {
    switch (status) {
      case "active": return "bg-emerald-500/10 text-emerald-700 border-emerald-200";
      case "paused": return "bg-warm-gold/10 text-warm-gold border-warm-gold/30";
      default: return "bg-muted/10 text-muted border-border-custom";
    }
  };

  return (
    <MobileSidebarProvider>
      <div className="min-h-screen bg-cream flex font-sans">
        <DashboardSidebar />

        <main className="flex-1 lg:pl-64 flex flex-col">
          <header className="sticky top-0 z-30 bg-cream/80 backdrop-blur-md border-b border-border-custom px-4 lg:px-8 py-4 flex items-center justify-between">
            <div>
              <h1 className="font-playfair text-2xl lg:text-3xl text-charcoal flex items-center gap-2">
                <Bot className="w-6 h-6 text-forest" />
                Autopilot Hunt
              </h1>
              <p className="text-muted font-dm mt-1">Set it and forget it. AI hunts properties for you 24/7.</p>
            </div>
          </header>

          <div className="p-4 lg:p-8 flex-1">
            {loading ? (
              <div className="flex justify-center items-center h-40">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-forest"></div>
              </div>
            ) : !hunt && !showCreateForm ? (
              /* No active hunt — show CTA */
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-20 bg-surface border border-border-custom rounded-2xl max-w-2xl mx-auto"
              >
                <div className="w-16 h-16 bg-forest/10 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Zap className="w-8 h-8 text-forest" />
                </div>
                <h3 className="text-2xl font-playfair text-charcoal mb-2">No Autopilot Hunt Active</h3>
                <p className="text-muted font-dm mb-8 max-w-md mx-auto">
                  Tell Griha AI what you&apos;re looking for and it will automatically search, match, 
                  and even run legal checks on properties — all while you sleep.
                </p>
                <button
                  onClick={() => setShowCreateForm(true)}
                  className="px-8 py-3 bg-forest text-cream rounded-xl font-dm font-semibold hover:bg-forest-light transition-colors inline-flex items-center gap-2"
                >
                  <Plus className="w-5 h-5" /> Start Autopilot Hunt
                </button>
              </motion.div>
            ) : showCreateForm && !hunt ? (
              /* Create form */
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-surface border border-border-custom rounded-2xl max-w-2xl mx-auto p-8"
              >
                <h3 className="font-playfair text-xl text-charcoal mb-6 flex items-center gap-2">
                  <Settings className="w-5 h-5 text-forest" /> Configure Your Hunt
                </h3>
                <div className="space-y-5">
                  <div className="relative">
                    <label className="block text-sm font-dm font-semibold text-charcoal mb-1">Target Locations <span className="text-muted font-normal">(comma separated)</span></label>
                    <input
                      type="text"
                      value={formLocations}
                      onChange={async (e) => {
                        const val = e.target.value;
                        setFormLocations(val);
                        
                        // Extract the current term being typed after the last comma
                        const parts = val.split(",");
                        const currentTerm = parts[parts.length - 1].trim();
                        
                        if (currentTerm.length > 2) {
                          setShowSuggestions(true);
                          setIsFetchingSuggestions(true);
                          try {
                            const res = await fetch(`${apiUrl}/api/locations/autocomplete?q=${encodeURIComponent(currentTerm)}`);
                            const data = await res.json();
                            setSuggestions(data || []);
                          } catch (err) {
                            console.error("Autocomplete error:", err);
                          } finally {
                            setIsFetchingSuggestions(false);
                          }
                        } else {
                          setShowSuggestions(false);
                        }
                      }}
                      onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                      onFocus={() => {
                        if (formLocations && formLocations.split(",").pop()?.trim().length! > 2) setShowSuggestions(true);
                      }}
                      placeholder="e.g. Powai, Andheri West, Bandra"
                      className="w-full px-4 py-2.5 border border-border-custom rounded-xl bg-cream text-charcoal font-dm focus:outline-none focus:ring-2 focus:ring-forest/30"
                    />
                    
                    {/* Autocomplete Dropdown */}
                    <AnimatePresence>
                      {showSuggestions && (
                        <motion.div
                          initial={{ opacity: 0, y: -10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -10 }}
                          className="absolute z-50 w-full mt-2 bg-cream border border-border-custom rounded-xl shadow-xl overflow-hidden max-h-60 overflow-y-auto"
                        >
                          {isFetchingSuggestions && suggestions.length === 0 ? (
                            <div className="px-4 py-3 text-sm font-dm text-muted flex items-center gap-2">
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-forest"></div>
                              Loading...
                            </div>
                          ) : suggestions.length > 0 ? (
                            <ul>
                              {suggestions.map((s, idx) => (
                                <li
                                  key={idx}
                                  onClick={() => {
                                    const parts = formLocations.split(",");
                                    parts[parts.length - 1] = " " + s;
                                    setFormLocations(parts.join(",").trim() + ", ");
                                    setShowSuggestions(false);
                                  }}
                                  className="px-4 py-2.5 hover:bg-forest/10 cursor-pointer font-dm text-charcoal text-sm flex items-center gap-2 border-b border-border-custom/50 last:border-0"
                                >
                                  <MapPin className="w-4 h-4 text-forest" />
                                  {s}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <div className="px-4 py-3 text-sm font-dm text-muted">
                              No locations found
                            </div>
                          )}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-dm font-semibold text-charcoal mb-1">BHK</label>
                      <select
                        value={formBhk}
                        onChange={(e) => setFormBhk(e.target.value)}
                        className="w-full px-4 py-2.5 border border-border-custom rounded-xl bg-cream text-charcoal font-dm focus:outline-none focus:ring-2 focus:ring-forest/30"
                      >
                        <option>1 BHK</option>
                        <option>2 BHK</option>
                        <option>3 BHK</option>
                        <option>4 BHK</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-dm font-semibold text-charcoal mb-1">Auto Legal Check</label>
                      <button
                        onClick={() => setFormAutoLegal(!formAutoLegal)}
                        className={`w-full px-4 py-2.5 border rounded-xl font-dm font-semibold transition-colors ${
                          formAutoLegal ? "bg-forest/10 text-forest border-forest/30" : "bg-cream text-muted border-border-custom"
                        }`}
                      >
                        {formAutoLegal ? "✓ Enabled" : "Disabled"}
                      </button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-dm font-semibold text-charcoal mb-1">Min Budget (₹/mo)</label>
                      <input
                        type="number"
                        value={formMinBudget}
                        onChange={(e) => setFormMinBudget(Number(e.target.value))}
                        className="w-full px-4 py-2.5 border border-border-custom rounded-xl bg-cream text-charcoal font-dm focus:outline-none focus:ring-2 focus:ring-forest/30"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-dm font-semibold text-charcoal mb-1">Max Budget (₹/mo)</label>
                      <input
                        type="number"
                        value={formMaxBudget}
                        onChange={(e) => setFormMaxBudget(Number(e.target.value))}
                        className="w-full px-4 py-2.5 border border-border-custom rounded-xl bg-cream text-charcoal font-dm focus:outline-none focus:ring-2 focus:ring-forest/30"
                      />
                    </div>
                  </div>
                  <div className="flex gap-3 pt-4">
                    <button
                      onClick={createHunt}
                      disabled={creating || !formLocations.trim()}
                      className="flex-1 px-6 py-3 bg-forest text-cream rounded-xl font-dm font-semibold hover:bg-forest-light transition-colors disabled:opacity-50 inline-flex items-center justify-center gap-2"
                    >
                      {creating ? "Launching..." : <><Zap className="w-4 h-4" /> Launch Hunt</>}
                    </button>
                    <button
                      onClick={() => setShowCreateForm(false)}
                      className="px-6 py-3 border border-border-custom text-charcoal rounded-xl font-dm font-semibold hover:bg-cream transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </motion.div>
            ) : hunt ? (
              /* Active/Paused hunt view */
              <div className="space-y-6 max-w-4xl">
                {/* Status bar */}
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-surface border border-border-custom rounded-2xl p-6"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${hunt.status === "active" ? "bg-emerald-500 animate-pulse" : "bg-warm-gold"}`} />
                      <span className={`px-3 py-1 rounded-full text-xs font-dm font-bold border ${statusColor(hunt.status)}`}>
                        {hunt.status.toUpperCase()}
                      </span>
                      <h2 className="font-playfair text-xl text-charcoal">
                        {hunt.bhk} in {hunt.locations.join(", ")}
                      </h2>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={toggleHunt}
                        className={`p-2.5 rounded-lg border transition-colors ${
                          hunt.status === "active" 
                            ? "border-warm-gold/30 text-warm-gold hover:bg-warm-gold/10" 
                            : "border-forest/30 text-forest hover:bg-forest/10"
                        }`}
                        title={hunt.status === "active" ? "Pause" : "Resume"}
                      >
                        {hunt.status === "active" ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                      </button>
                      <button
                        onClick={deleteHunt}
                        className="p-2.5 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 transition-colors"
                        title="Stop Hunt"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <div className="bg-cream rounded-xl p-4 border border-border-custom text-center">
                      <p className="font-dm font-bold text-2xl text-charcoal">{hunt.total_properties_found}</p>
                      <p className="text-xs text-muted font-dm">Total Matches</p>
                    </div>
                    <div className="bg-cream rounded-xl p-4 border border-border-custom text-center">
                      <p className="font-dm font-bold text-2xl text-charcoal">{hunt.matches.length}</p>
                      <p className="text-xs text-muted font-dm">Active Matches</p>
                    </div>
                    <div className="bg-cream rounded-xl p-4 border border-border-custom text-center">
                      <p className="font-dm font-bold text-2xl text-charcoal">
                        {hunt.matches.filter(m => m.legal_checked).length}
                      </p>
                      <p className="text-xs text-muted font-dm">Legal Checked</p>
                    </div>
                    <div className="bg-cream rounded-xl p-4 border border-border-custom text-center">
                      <p className="font-dm font-bold text-2xl text-charcoal">
                        ₹{(hunt.min_budget / 1000).toFixed(0)}k–{(hunt.max_budget / 1000).toFixed(0)}k
                      </p>
                      <p className="text-xs text-muted font-dm">Budget Range</p>
                    </div>
                  </div>
                </motion.div>

                {/* Matches list */}
                <div className="bg-surface border border-border-custom rounded-2xl overflow-hidden">
                  <div className="p-5 border-b border-border-custom">
                    <h3 className="font-dm font-bold text-charcoal flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-forest" /> Matched Properties
                    </h3>
                  </div>
                  {hunt.matches.length === 0 ? (
                    <div className="p-8 text-center text-muted font-dm">
                      <Clock className="w-8 h-8 mx-auto mb-2 text-muted/40" />
                      No matches yet. The autopilot will find properties on its next run.
                    </div>
                  ) : (
                    <div className="divide-y divide-border-custom">
                      {hunt.matches
                        .sort((a, b) => b.match_score - a.match_score)
                        .map((match, idx) => (
                        <Link
                          key={match.property_id}
                          href={`/property/${match.property_id}`}
                          className="flex items-center justify-between p-4 hover:bg-cream/50 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                              match.match_score >= 80 ? "bg-emerald-100 text-emerald-700" :
                              match.match_score >= 60 ? "bg-warm-gold/20 text-warm-gold" :
                              "bg-red-100 text-red-600"
                            }`}>
                              {match.match_score}%
                            </div>
                            <div>
                              <p className="font-dm font-semibold text-charcoal text-sm">
                                Property #{match.property_id.slice(-6)}
                              </p>
                              <p className="text-xs text-muted">
                                Found {new Date(match.found_at).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {match.legal_checked && (
                              <span className={`text-xs px-2 py-1 rounded-full font-dm font-semibold ${
                                match.legal_status === "low" ? "bg-emerald-100 text-emerald-700" :
                                match.legal_status === "medium" ? "bg-warm-gold/20 text-warm-gold" :
                                "bg-red-100 text-red-600"
                              }`}>
                                Legal: {match.legal_status || "checked"}
                              </span>
                            )}
                            {!match.legal_checked && (
                              <span className="text-xs px-2 py-1 rounded-full bg-muted/10 text-muted font-dm">
                                No legal check
                              </span>
                            )}
                          </div>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </main>
      </div>
    </MobileSidebarProvider>
  );
}
