"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { useState, useRef, useEffect, createContext, useContext } from "react";
import { SignedIn, SignedOut, SignInButton, UserButton, useUser } from "@clerk/nextjs";
import { NotificationBell } from "./NotificationBell";
import {
  Home,
  Search,
  Scale,
  MessageSquare,
  FileText,
  MapPin,
  Settings,
  Activity,
  Bell,
  BarChart3,
  SlidersHorizontal,
  LocateFixed,
  Loader2,
  Menu,
  X,
  Zap,
  Calendar,
  Sparkles,
} from "lucide-react";

// Context so pages can control sidebar open state
const MobileSidebarContext = createContext<{
  isOpen: boolean;
  toggle: () => void;
  close: () => void;
}>({
  isOpen: false,
  toggle: () => {},
  close: () => {},
});

export function useMobileSidebar() {
  return useContext(MobileSidebarContext);
}

export function MobileSidebarProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);
  const toggle = () => setIsOpen((p) => !p);
  const close = () => setIsOpen(false);

  return (
    <MobileSidebarContext.Provider value={{ isOpen, toggle, close }}>
      {children}
    </MobileSidebarContext.Provider>
  );
}

const NAV_ITEMS = [
  { label: "My Matches", href: "/dashboard", icon: Home, badge: 8 },
  { label: "Pipeline", href: "/pipeline", icon: BarChart3 },
  { label: "Price Drop Alerts", href: "/price-drop-alerts", icon: Bell },

  { label: "Scheduled Visits", href: "/visits", icon: Calendar },
  { label: "Legal Checks", href: "/legal/prop-1", icon: Scale },
  { label: "Negotiations", href: "/negotiate/prop-1", icon: MessageSquare },
  { label: "Market Insights", href: "/market", icon: MapPin },
  { label: "Documents", href: "/documents", icon: FileText },
  { label: "Neighbourhood", href: "/neighbourhood", icon: MapPin },
  { label: "Activity Feed", href: "/activity", icon: Activity },
  { label: "Preferences", href: "/preferences", icon: Settings },
];

export function DashboardSidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user, isSignedIn } = useUser();
  const { isOpen, close } = useMobileSidebar();

  const preferredLocation = searchParams.get("location") || "";
  const preferredBhk = searchParams.get("bhk") || "Any BHK";
  const displayName = user?.fullName || user?.firstName || "Home Seeker";
  const preferenceLabel = preferredLocation
    ? `${preferredBhk} in ${preferredLocation}`
    : "Set location and BHK to personalize matches";

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="px-6 py-6 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-1">
          <span className="font-playfair italic text-2xl text-charcoal">griha</span>
          <span className="font-playfair text-2xl text-warm-gold font-bold">AI</span>
        </Link>
        {/* Close button - mobile only */}
        <button onClick={close} className="lg:hidden p-1 text-muted hover:text-charcoal">
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* User greeting */}
      <div className="px-6 pb-4 border-b border-border-custom">
        <p className="text-sm text-muted">Welcome back,</p>
        <p className="font-dm font-semibold text-charcoal">{isSignedIn ? displayName : "Guest"}</p>
        <p className="text-xs text-muted mt-1">{preferenceLabel}</p>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href.split("#")[0] + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={close}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-dm transition-all",
                isActive
                  ? "bg-forest/10 text-forest font-semibold"
                  : "text-muted hover:bg-cream hover:text-charcoal"
              )}
            >
              <item.icon className="w-5 h-5" />
              <span className="flex-1">{item.label}</span>
              {item.badge && (
                <span className="bg-forest text-white text-xs px-2 py-0.5 rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
    </>
  );

  return (
    <>
      {/* Desktop sidebar - always visible on lg+ */}
      <aside className="hidden lg:flex fixed left-0 top-0 bottom-0 w-[260px] bg-surface border-r border-border-custom flex-col z-40">
        {sidebarContent}
      </aside>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={close}
              className="fixed inset-0 bg-charcoal/40 backdrop-blur-sm z-50 lg:hidden"
            />
            {/* Drawer */}
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              className="fixed left-0 top-0 bottom-0 w-[280px] bg-surface border-r border-border-custom flex flex-col z-50 lg:hidden"
            >
              {sidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

export interface DashboardSearchFilters {
  location: string;
  bhk: string;
  gated: boolean;
  pet: boolean;
  parking: boolean;
}

interface DashboardTopBarProps {
  filters?: DashboardSearchFilters;
  onApplyFilters?: (filters: DashboardSearchFilters) => void;
}

export function DashboardTopBar({ filters, onApplyFilters }: DashboardTopBarProps) {
  const mobileSidebar = useMobileSidebar();
  const [isSearchExpanded, setIsSearchExpanded] = useState(false);
  const [draftFilters, setDraftFilters] = useState<DashboardSearchFilters>(filters || {
    location: "",
    bhk: "Any BHK",
    gated: false,
    pet: false,
    parking: false,
  });
  const [locationSuggestions, setLocationSuggestions] = useState<string[]>([]);
  const [locating, setLocating] = useState(false);
  const [locationStatus, setLocationStatus] = useState("");
  const searchRef = useRef<HTMLDivElement>(null);
  const [aiMode, setAiMode] = useState(false);
  const [aiQuery, setAiQuery] = useState("");
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    if (filters) setDraftFilters(filters);
  }, [filters]);

  // Close search when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsSearchExpanded(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (!isSearchExpanded || !draftFilters.location.trim()) {
      setLocationSuggestions([]);
      return;
    }

    const controller = new AbortController();
    const timeout = window.setTimeout(async () => {
      try {
        setLoadingSuggestions(true);
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/locations/autocomplete?q=${encodeURIComponent(draftFilters.location.trim())}`,
          { signal: controller.signal }
        );

        if (!res.ok) {
          setLocationSuggestions([]);
          return;
        }

        const json = await res.json();
        setLocationSuggestions(Array.isArray(json) ? json : []);
      } catch (err: unknown) {
        if (!(err instanceof DOMException && err.name === "AbortError")) {
          setLocationSuggestions([]);
        }
      } finally {
        setLoadingSuggestions(false);
      }
    }, 280);

    return () => {
      controller.abort();
      window.clearTimeout(timeout);
    };
  }, [draftFilters.location, isSearchExpanded]);

  const toggleAmenity = (key: "gated" | "pet" | "parking") => {
    setDraftFilters((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleUseCurrentLocation = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();

    if (typeof window === "undefined" || !("geolocation" in navigator)) {
      setLocationStatus("Geolocation is not supported in this browser.");
      return;
    }

    setLocating(true);
    setLocationStatus("Requesting location permission...");

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          setLocationStatus("Detecting your locality...");

          const params = new URLSearchParams({
            lat: String(position.coords.latitude),
            lon: String(position.coords.longitude),
          });

          const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:10000'}/api/locations/reverse?${params.toString()}`);
          if (!response.ok) {
            throw new Error("reverse_geocode_failed");
          }

          const payload = await response.json();
          const detectedLocation = typeof payload?.location === "string" ? payload.location.trim() : "";

          if (!detectedLocation) {
            throw new Error("location_not_found");
          }

          const nextFilters = { ...draftFilters, location: detectedLocation };
          setDraftFilters(nextFilters);
          if (onApplyFilters) onApplyFilters(nextFilters);
          setIsSearchExpanded(false);
          setLocationSuggestions([]);
          setLocationStatus(`Showing properties near ${detectedLocation}`);
        } catch {
          setLocationStatus("Unable to detect your location right now. Please try again.");
        } finally {
          setLocating(false);
          window.setTimeout(() => setLocationStatus(""), 4500);
        }
      },
      (error) => {
        const messageByCode: Record<number, string> = {
          1: "Location access denied. Please allow permission and try again.",
          2: "Location unavailable. Please try again in a few seconds.",
          3: "Location request timed out. Please try again.",
        };
        setLocating(false);
        setLocationStatus(messageByCode[error.code] || "Unable to read your location.");
        window.setTimeout(() => setLocationStatus(""), 4500);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000,
      }
    );
  };

  const applyFilters = () => {
    if (onApplyFilters) onApplyFilters(draftFilters);
    setIsSearchExpanded(false);
    setLocationSuggestions([]);
  };

  return (
    <div className="sticky top-0 z-30 bg-cream/90 backdrop-blur-md border-b border-border-custom">
      <div className="flex items-center px-3 sm:px-6 py-3 min-h-[60px] lg:min-h-[72px] gap-2 sm:gap-4">
        {/* Mobile hamburger */}
        <button
          onClick={mobileSidebar.toggle}
          className="lg:hidden p-2 text-charcoal hover:bg-sand rounded-xl transition-colors shrink-0"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Status indicators - hidden on small mobile */}
        <div className="hidden sm:flex items-center gap-2 lg:gap-4 min-w-0 shrink-0">
          <div className="flex items-center gap-1.5 bg-surface/50 border border-border-custom px-2 sm:px-3 py-1.5 rounded-full shrink-0">
            <motion.span
              className="w-2 h-2 rounded-full bg-success"
              animate={{ scale: [1, 1.2, 1], opacity: [0.7, 1, 0.7] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
            <span className="text-[12px] sm:text-[13px] text-charcoal font-dm">
              <span className="font-bold">1,247</span> <span className="text-muted hidden md:inline">searched</span>
            </span>
          </div>
          <div className="hidden md:flex items-center gap-1.5 bg-forest/5 border border-forest/10 px-3 py-1.5 rounded-full shrink-0">
            <span className="font-bold text-forest text-[13px]">8</span>
            <span className="text-forest/70 text-[13px] font-dm">new matches</span>
          </div>
        </div>

        {/* Global Advanced Search Center */}
        <div 
          ref={searchRef}
          className={cn(
            "relative transition-all duration-300 ease-out z-50 flex-1 sm:flex-none",
            isSearchExpanded ? "sm:w-[500px] w-full" : "sm:w-[250px] md:w-[300px] w-full"
          )}
        >
          <div 
            className={cn(
              "bg-surface border-border-custom rounded-2xl shadow-sm transition-all",
              isSearchExpanded ? "border shadow-xl overflow-visible" : "border hover:shadow-md cursor-pointer overflow-hidden"
            )}
            onClick={() => !isSearchExpanded && setIsSearchExpanded(true)}
          >
            {/* The collapsed view / Search Input row */}
            <div className="flex items-center px-2 py-1.5 h-10 sm:h-12">
              <div className="flex-1 flex items-center px-2 sm:px-3 relative">
                  <div className="w-full bg-transparent text-sm font-dm focus:outline-none text-charcoal flex items-center">
                    {aiMode ? (
                      <input
                        type="text"
                        placeholder="Describe your ideal home (e.g. 2 BHK in Bandra under 1L with gym)"
                        value={aiQuery}
                        onChange={(e) => setAiQuery(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            e.stopPropagation();
                            handleAiSearch();
                          }
                        }}
                        className="w-full bg-transparent outline-none placeholder:text-muted"
                        autoFocus
                      />
                    ) : (
                      <input
                        id="location-search"
                        name="location-search"
                        type="text"
                        placeholder="Where do you want to live?"
                        value={draftFilters.location}
                        onChange={(e) => setDraftFilters((prev) => ({ ...prev, location: e.target.value }))}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") {
                            e.preventDefault();
                            e.stopPropagation();
                            applyFilters();
                          }
                        }}
                        className="w-full bg-transparent outline-none placeholder:text-muted"
                        autoComplete="off"
                      />
                    )}
                  </div>

                {!aiMode && isSearchExpanded && (locationSuggestions.length > 0 || loadingSuggestions) && (
                  <div className="absolute left-0 right-0 top-full mt-2 z-50 bg-surface border border-border-custom rounded-xl shadow-lg overflow-hidden">
                    {loadingSuggestions && (
                      <div className="px-4 py-2.5 text-xs font-dm text-muted">Searching locations...</div>
                    )}
                    {!loadingSuggestions && locationSuggestions.map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={(e) => {
                          e.stopPropagation();
                          setDraftFilters((prev) => ({ ...prev, location: suggestion }));
                          setLocationSuggestions([]);
                        }}
                        className="block w-full text-left px-4 py-2.5 text-sm font-dm text-charcoal hover:bg-cream transition-colors"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {!aiMode && (
                <button
                  type="button"
                  onClick={handleUseCurrentLocation}
                  disabled={locating}
                  className="px-2 sm:px-3 h-9 border-l border-border-custom text-sm font-dm text-muted hover:text-charcoal transition-colors flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
                  title="Use my current location"
                >
                  {locating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <LocateFixed className="w-4 h-4" />
                  )}
                  <span className="hidden xl:inline">Near Me</span>
                </button>
              )}
              
              {!isSearchExpanded && !aiMode && (
                <div className="hidden sm:flex px-3 border-l border-border-custom text-sm font-dm text-muted items-center gap-2">
                  <SlidersHorizontal className="w-4 h-4" />
                  <span className="hidden md:inline">Filters</span>
                </div>
              )}

              {isSearchExpanded && !aiMode && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    applyFilters();
                  }}
                  className="px-3 sm:px-5 py-2 mr-1 bg-forest text-white text-sm font-semibold rounded-xl hover:bg-forest-light transition-colors shadow-sm"
                >
                  Search
                </button>
              )}
              
              {aiMode && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAiSearch();
                  }}
                  disabled={aiLoading}
                  className="px-3 sm:px-5 py-2 mr-1 bg-[#1A1A1A] text-white text-sm font-semibold rounded-xl hover:bg-charcoal transition-colors shadow-sm flex items-center gap-2"
                >
                  {aiLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                  Ask AI
                </button>
              )}
              
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setAiMode(!aiMode);
                  if (!isSearchExpanded) setIsSearchExpanded(true);
                }}
                className={`ml-1 px-3 h-9 flex items-center gap-2 rounded-xl transition-colors ${aiMode ? "text-[#1A1A1A] bg-sand" : "text-muted hover:text-charcoal hover:bg-cream"}`}
                title="Toggle AI Search Mode"
              >
                <Sparkles className="w-4 h-4" />
                <span className="hidden sm:inline text-xs font-dm font-semibold uppercase">{aiMode ? "Classic" : "AI Mode"}</span>
              </button>
            </div>

            {/* Expanded Content Panel */}
            <AnimatePresence>
              {isSearchExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="border-t border-border-custom bg-surface px-3 sm:px-5 py-4 grid grid-cols-1 sm:grid-cols-3 gap-4"
                >
                  {/* Dropdown for BHK */}
                  <div className="flex flex-col gap-1.5 min-w-0">
                    <span className="text-xs font-dm text-muted font-medium uppercase tracking-wider">SIZE</span>
                    <select 
                      value={draftFilters.bhk}
                      onChange={(e) => setDraftFilters((prev) => ({ ...prev, bhk: e.target.value }))}
                      className="bg-cream border border-border-custom text-sm text-charcoal font-dm rounded-lg px-3 py-2 outline-none focus:border-forest"
                    >
                      <option>Any BHK</option>
                      <option>1 BHK</option>
                      <option>2 BHK</option>
                      <option>3 BHK</option>
                      <option>4+ BHK</option>
                    </select>
                  </div>

                  <div className="flex flex-col gap-1.5 sm:col-span-2">
                    <span className="text-xs font-dm text-muted font-medium uppercase tracking-wider">AMENITIES</span>
                    <div className="flex flex-wrap gap-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleAmenity("gated");
                        }}
                        className={cn(
                          "px-2.5 py-1 text-xs rounded-full border font-dm",
                          draftFilters.gated
                            ? "bg-forest text-white border-forest"
                            : "bg-cream text-charcoal border-border-custom"
                        )}
                      >
                        Gated
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleAmenity("pet");
                        }}
                        className={cn(
                          "px-2.5 py-1 text-xs rounded-full border font-dm",
                          draftFilters.pet
                            ? "bg-forest text-white border-forest"
                            : "bg-cream text-charcoal border-border-custom"
                        )}
                      >
                        Pet Friendly
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleAmenity("parking");
                        }}
                        className={cn(
                          "px-2.5 py-1 text-xs rounded-full border font-dm",
                          draftFilters.parking
                            ? "bg-forest text-white border-forest"
                            : "bg-cream text-charcoal border-border-custom"
                        )}
                      >
                        Parking
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {locationStatus && (
            <p className={cn(
              "mt-2 px-3 text-xs font-dm",
              locationStatus.toLowerCase().includes("unable") || locationStatus.toLowerCase().includes("denied")
                ? "text-danger"
                : "text-forest"
            )}>
              {locationStatus}
            </p>
          )}
        </div>

        {/* Right side interactions */}
        <div className="flex items-center justify-end gap-2 sm:gap-3 shrink-0">
          <NotificationBell />
          
          <SignedIn>
            <UserButton afterSignOutUrl="/" appearance={{ elements: { avatarBox: "w-9 h-9 sm:w-10 sm:h-10 border-2 border-forest/20" } }} />
          </SignedIn>
          <SignedOut>
            <SignInButton mode="modal">
              <button className="px-4 py-2 bg-forest text-white rounded-xl font-dm text-sm font-semibold hover:bg-forest-light transition-colors">
                Sign in
              </button>
            </SignInButton>
          </SignedOut>
          <Link href="/activity" className="p-2 sm:p-2.5 bg-surface border border-border-custom hover:border-forest/50 rounded-xl transition-all hover:shadow-sm">
            <Activity className="w-4 h-4 text-charcoal" />
          </Link>
        </div>
      </div>
    </div>
  );
}
