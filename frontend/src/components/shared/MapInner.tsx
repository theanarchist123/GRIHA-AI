"use client";

import { useEffect, useRef } from "react";

interface MapInnerProps {
  center: { lat: number; lng: number; address: string };
  markers: any[];
  onMarkerClick: (name: string) => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  school: "#3b82f6",       // blue
  hospital: "#ef4444",     // red
  metro: "#8b5cf6",        // violet
  hotel: "#f59e0b",        // gold
  supermarket: "#22c55e",  // green
  property: "#1c1c1c",     // black
  default: "#6b7280",      // grey
};

const CATEGORY_LABELS: Record<string, string> = {
  school: "School",
  hospital: "Hospital",
  metro: "Metro / Transit",
  hotel: "Hotel",
  supermarket: "Supermarket",
};

function createSvgIcon(color: string): string {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="24" height="36">
      <path d="M12 0C5.373 0 0 5.373 0 12c0 9 12 24 12 24S24 21 24 12C24 5.373 18.627 0 12 0z" fill="${color}" stroke="white" stroke-width="1.5"/>
      <circle cx="12" cy="12" r="5" fill="white"/>
    </svg>
  `.trim();
  return "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(svg);
}

export default function MapInner({ center, markers, onMarkerClick }: MapInnerProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<any>(null);
  const isMounted = useRef(false);

  useEffect(() => {
    if (!mapRef.current || isMounted.current) return;
    isMounted.current = true;

    // Dynamically import Leaflet so it's never executed on the server
    import("leaflet").then((L) => {
      import("leaflet/dist/leaflet.css");
      
      // Safety check in case it's already initialized
      if (mapRef.current && (mapRef.current as any)._leaflet_id) {
        return;
      }

      const map = L.map(mapRef.current!, {
        center: [center.lat, center.lng],
        zoom: 14,
        scrollWheelZoom: true,
      });
      leafletMapRef.current = map;

      // Carto Voyager tile layer (clean, modern look)
      L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      const makeIcon = (color: string) =>
        L.icon({
          iconUrl: createSvgIcon(color),
          iconSize: [24, 36],
          iconAnchor: [12, 36],
          popupAnchor: [0, -36],
        });

      // Property center marker
      L.marker([center.lat, center.lng], { icon: makeIcon(CATEGORY_COLORS.property) })
        .addTo(map)
        .bindPopup(
          `<div style="font-family:sans-serif;font-size:12px;font-weight:700;color:#1c1c1c">📍 This Property</div>
           <div style="font-size:11px;color:#888;margin-top:3px">${center.address}</div>`
        );

      // Amenity markers
      markers.forEach((marker) => {
        const color = CATEGORY_COLORS[marker.category] || CATEGORY_COLORS.default;
        const label = CATEGORY_LABELS[marker.category] || marker.category;

        const m = L.marker([marker.lat, marker.lng], { icon: makeIcon(color) })
          .addTo(map);

        const safeName = marker.name.replace(/'/g, "\\'");
        const popupHtml = `
          <div style="font-family:sans-serif;min-width:160px">
            <div style="font-weight:700;font-size:13px;color:#1c1c1c;margin-bottom:4px">${marker.name}</div>
            <span style="font-size:10px;background:${color}22;color:${color};padding:2px 8px;border-radius:999px;font-weight:600;text-transform:uppercase">${label}</span>
            <div style="font-size:11px;color:#888;margin-top:6px">${marker.distance_m}m away</div>
            <button
              onclick="window.__grihaMarkerClick && window.__grihaMarkerClick('${safeName}')"
              style="margin-top:8px;width:100%;padding:6px 0;background:#1c1c1c;color:#fff;border:none;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer"
            >Calculate Commute →</button>
          </div>
        `;
        m.bindPopup(popupHtml);
      });

      // Expose click handler to window for use inside popup HTML
      (window as any).__grihaMarkerClick = (name: string) => {
        onMarkerClick(name);
        map.closePopup();
      };
    });

    return () => {
      if (leafletMapRef.current) {
        leafletMapRef.current.remove();
        leafletMapRef.current = null;
      }
      isMounted.current = false;
    };
  }, []); // intentionally run only once on mount

  // Update click handler reference without rebuilding the map
  useEffect(() => {
    (window as any).__grihaMarkerClick = (name: string) => {
      onMarkerClick(name);
      leafletMapRef.current?.closePopup();
    };
  }, [onMarkerClick]);

  return (
    <div
      ref={mapRef}
      style={{ height: "100%", width: "100%", borderRadius: "16px" }}
    />
  );
}
