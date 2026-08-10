"use client";

import { useState, useEffect } from "react";
import { Bell } from "lucide-react";
import { useUser } from "@clerk/nextjs";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { usePathname } from "next/navigation";

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  priority: string;
  read: boolean;
  action_url: string | null;
  created_at: string;
}

export function NotificationBell() {
  const { user } = useUser();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    if (user?.id) {
      fetchNotifications();
      // Poll every 1 minute
      const interval = setInterval(fetchNotifications, 60000);
      return () => clearInterval(interval);
    }
  }, [user?.id]);

  useEffect(() => {
    // Close dropdown on route change
    setIsOpen(false);
  }, [pathname]);

  const fetchNotifications = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";
      const res = await fetch(`${apiUrl}/api/notifications/?clerk_id=${user?.id}&limit=5`);
      const json = await res.json();
      if (json.data) {
        setNotifications(json.data);
        setUnreadCount(json.data.filter((n: Notification) => !n.read).length);
      }
    } catch (err) {
      console.error("Failed to fetch notifications", err);
    }
  };

  const markAsRead = async (id: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";
      await fetch(`${apiUrl}/api/notifications/${id}/read`, { method: "PATCH" });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-charcoal hover:bg-cream rounded-xl transition-colors"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border border-surface" />
        )}
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 mt-2 w-80 bg-surface border border-border-custom rounded-2xl shadow-xl z-50 overflow-hidden"
            >
              <div className="p-4 border-b border-border-custom flex items-center justify-between bg-cream/50">
                <h3 className="font-playfair text-charcoal font-semibold">Notifications</h3>
                {unreadCount > 0 && (
                  <span className="text-xs font-dm bg-forest/10 text-forest px-2 py-0.5 rounded-full">
                    {unreadCount} new
                  </span>
                )}
              </div>
              
              <div className="max-h-[300px] overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="p-6 text-center text-muted font-dm text-sm">
                    No notifications yet.
                  </div>
                ) : (
                  <div className="divide-y divide-border-custom">
                    {notifications.map(notif => (
                      <div 
                        key={notif.id}
                        className={`p-4 transition-colors ${notif.read ? "bg-surface opacity-75" : "bg-cream/30"}`}
                      >
                        <div className="flex gap-3">
                          <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                            notif.read ? "bg-transparent" : 
                            notif.priority === "high" ? "bg-red-500" : "bg-forest"
                          }`} />
                          <div>
                            <p className="text-sm font-dm font-semibold text-charcoal">{notif.title}</p>
                            <p className="text-xs font-dm text-muted mt-0.5 leading-relaxed">{notif.message}</p>
                            <div className="flex items-center gap-3 mt-2">
                              <span className="text-[10px] text-muted/70 font-dm">
                                {new Date(notif.created_at).toLocaleDateString()}
                              </span>
                              {!notif.read && (
                                <button 
                                  onClick={(e) => { e.preventDefault(); markAsRead(notif.id); }}
                                  className="text-[10px] text-forest font-dm font-medium hover:underline"
                                >
                                  Mark as read
                                </button>
                              )}
                              {notif.action_url && (
                                <Link 
                                  href={notif.action_url}
                                  onClick={() => markAsRead(notif.id)}
                                  className="text-[10px] text-warm-gold font-dm font-medium hover:underline"
                                >
                                  View detail
                                </Link>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="p-3 border-t border-border-custom bg-cream/50 text-center">
                <Link href="/notifications" className="text-xs font-dm font-semibold text-forest hover:text-forest-light">
                  View all notifications
                </Link>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
