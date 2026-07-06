"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface PointOfInterest {
  name: string;
  lat: number;
  lng: number;
  distance_m: number;
  tags?: Record<string, string>;
}

interface MapProps {
  center: { lat: number; lng: number; address: string };
  markers: PointOfInterest[];
}

// Fix Leaflet's default icon path issue with webpack
const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const homeIcon = L.icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-gold.png",
  iconRetinaUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-gold.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

L.Marker.prototype.options.icon = defaultIcon;

export default function MapComponent({ center, markers }: MapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const homeMarkerRef = useRef<L.Marker | null>(null);

  // Initialize the map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [center.lat, center.lng],
      zoom: 15,
      scrollWheelZoom: true,
    });

    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }
    ).addTo(map);

    // Home marker
    const homeMarker = L.marker([center.lat, center.lng], { icon: homeIcon })
      .addTo(map)
      .bindPopup(
        `<div style="font-weight:600">Selected Property</div><div style="font-size:12px;color:#666;margin-top:4px">${center.address}</div>`
      );

    // Layer group for POI markers
    const markersLayer = L.layerGroup().addTo(map);

    mapRef.current = map;
    markersLayerRef.current = markersLayer;
    homeMarkerRef.current = homeMarker;

    // Force a resize after mount (fixes grey tiles bug)
    setTimeout(() => map.invalidateSize(), 200);

    return () => {
      map.remove();
      mapRef.current = null;
      markersLayerRef.current = null;
      homeMarkerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update center when it changes
  useEffect(() => {
    if (!mapRef.current || !homeMarkerRef.current) return;

    const map = mapRef.current;
    homeMarkerRef.current.setLatLng([center.lat, center.lng]);
    homeMarkerRef.current.setPopupContent(
      `<div style="font-weight:600">Selected Property</div><div style="font-size:12px;color:#666;margin-top:4px">${center.address}</div>`
    );

    if (markers.length === 0) {
      map.setView([center.lat, center.lng], 15);
    }
  }, [center, markers.length]);

  // Update POI markers when they change
  useEffect(() => {
    if (!mapRef.current || !markersLayerRef.current) return;

    const map = mapRef.current;
    const layer = markersLayerRef.current;

    // Clear old POI markers
    layer.clearLayers();

    if (markers.length > 0) {
      // Add new markers
      markers.forEach((m) => {
        L.marker([m.lat, m.lng], { icon: defaultIcon })
          .addTo(layer)
          .bindPopup(
            `<div style="font-weight:600">${m.name}</div><div style="font-size:12px;color:#666;margin-top:4px">${m.distance_m}m away</div>`
          );
      });

      // Fit bounds to include home + all POIs
      const bounds = L.latLngBounds([[center.lat, center.lng]]);
      markers.forEach((m) => bounds.extend([m.lat, m.lng]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
    }
  }, [markers, center.lat, center.lng]);

  return (
    <div
      ref={containerRef}
      className="w-full h-full rounded-2xl overflow-hidden border border-dark-border shadow-sm"
      style={{ zIndex: 0 }}
    />
  );
}
