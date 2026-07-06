"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Calendar, Clock, X, CalendarPlus } from "lucide-react";

interface ScheduleVisitModalProps {
  isOpen: boolean;
  onClose: () => void;
  propertyTitle: string;
  propertyAddress: string;
}

export function ScheduleVisitModal({ isOpen, onClose, propertyTitle, propertyAddress }: ScheduleVisitModalProps) {
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");

  const handleDownloadIcs = () => {
    if (!date || !time) {
      alert("Please select a date and time.");
      return;
    }

    const startDateTime = new Date(`${date}T${time}`);
    const endDateTime = new Date(startDateTime.getTime() + 60 * 60 * 1000); // 1 hour duration

    const formatDate = (d: Date) => {
      return d.toISOString().replace(/-|:|\.\d+/g, "");
    };

    const icsContent = `BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Griha AI//Property Visit//EN
BEGIN:VEVENT
DTSTART:${formatDate(startDateTime)}
DTEND:${formatDate(endDateTime)}
SUMMARY:Property Visit: ${propertyTitle}
LOCATION:${propertyAddress}
DESCRIPTION:Scheduled visit for ${propertyTitle} via Griha AI.
END:VEVENT
END:VCALENDAR`;

    const blob = new Blob([icsContent], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Visit_${propertyTitle.replace(/\s+/g, "_")}.ics`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    onClose(); // Close modal after scheduling
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-charcoal/50 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="bg-cream rounded-2xl w-full max-w-md overflow-hidden shadow-2xl border border-border-custom"
          >
            <div className="p-5 border-b border-border-custom bg-surface flex items-center justify-between">
              <h3 className="font-dm font-bold text-charcoal flex items-center gap-2">
                <Calendar className="w-5 h-5 text-forest" />
                Schedule a Visit
              </h3>
              <button 
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-border-custom/50 text-muted transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6">
              <div className="mb-5 p-4 bg-forest/5 border border-forest/10 rounded-xl">
                <p className="text-sm font-dm font-semibold text-charcoal">{propertyTitle}</p>
                <p className="text-xs font-dm text-muted mt-1">{propertyAddress}</p>
              </div>

              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-xs font-dm font-semibold text-muted mb-2">Select Date</label>
                  <div className="relative">
                    <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                    <input
                      type="date"
                      value={date}
                      onChange={(e) => setDate(e.target.value)}
                      className="w-full pl-9 pr-4 py-2.5 bg-surface border border-border-custom rounded-xl text-sm font-dm focus:outline-none focus:border-forest"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-dm font-semibold text-muted mb-2">Select Time</label>
                  <div className="relative">
                    <Clock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
                    <input
                      type="time"
                      value={time}
                      onChange={(e) => setTime(e.target.value)}
                      className="w-full pl-9 pr-4 py-2.5 bg-surface border border-border-custom rounded-xl text-sm font-dm focus:outline-none focus:border-forest"
                    />
                  </div>
                </div>
              </div>

              <button 
                onClick={handleDownloadIcs}
                disabled={!date || !time}
                className="w-full py-3 bg-forest text-cream font-dm font-bold rounded-xl transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <CalendarPlus className="w-4 h-4" />
                Add to Calendar
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
