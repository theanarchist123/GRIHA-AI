"use client";

import { useState, useEffect } from "react";
import { MobileSidebarProvider, DashboardSidebar } from "@/components/shared/Navbar";
import { Bell, CheckCircle2, Trash2 } from "lucide-react";
import { useUser } from "@clerk/nextjs";
import Link from "next/link";

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

export default function NotificationsPage() {
  const { user } = useUser();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.id) fetchNotifications();
  }, [user?.id]);

  const fetchNotifications = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";
      const res = await fetch(`${apiUrl}/api/notifications/?clerk_id=${user?.id}&limit=100`);
      const json = await res.json();
      if (json.data) {
        setNotifications(json.data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const markAllRead = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";
      await fetch(`${apiUrl}/api/notifications/read-all?clerk_id=${user?.id}`, { method: "POST" });
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    } catch (err) {
      console.error(err);
    }
  };

  const clearAll = async () => {
    if (!confirm("Clear all notifications?")) return;
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";
      await fetch(`${apiUrl}/api/notifications/clear-all?clerk_id=${user?.id}`, { method: "DELETE" });
      setNotifications([]);
    } catch (err) {
      console.error(err);
    }
  };

  const markAsRead = async (id: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:10000";
      await fetch(`${apiUrl}/api/notifications/${id}/read`, { method: "PATCH" });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    } catch (err) {
      console.error(err);
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
                <Bell className="w-6 h-6 text-forest" />
                Notifications
              </h1>
            </div>
            
            <div className="flex gap-2">
              <button 
                onClick={markAllRead}
                className="px-4 py-2 bg-forest/10 text-forest text-sm font-dm font-semibold rounded-lg hover:bg-forest/20 transition-colors flex items-center gap-2"
              >
                <CheckCircle2 className="w-4 h-4" /> Mark all read
              </button>
              <button 
                onClick={clearAll}
                className="px-4 py-2 bg-surface border border-border-custom text-muted text-sm font-dm font-semibold rounded-lg hover:bg-cream transition-colors flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" /> Clear all
              </button>
            </div>
          </header>

          <div className="p-4 lg:p-8 flex-1 max-w-4xl mx-auto w-full">
            {loading ? (
              <div className="flex justify-center mt-20">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-forest"></div>
              </div>
            ) : notifications.length === 0 ? (
              <div className="text-center mt-20 bg-surface border border-border-custom rounded-2xl p-10">
                <Bell className="w-12 h-12 text-muted/30 mx-auto mb-4" />
                <h3 className="font-playfair text-xl text-charcoal mb-2">You&apos;re all caught up!</h3>
                <p className="font-dm text-muted">No new notifications to show.</p>
              </div>
            ) : (
              <div className="bg-surface border border-border-custom rounded-2xl overflow-hidden divide-y divide-border-custom shadow-sm">
                {notifications.map(notif => (
                  <div key={notif.id} className={`p-5 flex gap-4 ${notif.read ? "bg-surface" : "bg-forest/5"}`}>
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                      notif.priority === "high" ? "bg-red-100 text-red-600" : "bg-emerald-100 text-emerald-700"
                    }`}>
                      <Bell className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-dm font-bold text-charcoal">{notif.title}</h4>
                      <p className="font-dm text-muted mt-1">{notif.message}</p>
                      
                      <div className="flex items-center gap-4 mt-3">
                        <span className="text-xs font-dm text-muted/60">
                          {new Date(notif.created_at).toLocaleString()}
                        </span>
                        
                        {!notif.read && (
                          <button 
                            onClick={() => markAsRead(notif.id)}
                            className="text-xs font-dm font-medium text-forest hover:underline"
                          >
                            Mark as read
                          </button>
                        )}
                        
                        {notif.action_url && (
                          <Link 
                            href={notif.action_url}
                            className="text-xs font-dm font-medium text-warm-gold hover:underline"
                          >
                            Go to detail &rarr;
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </MobileSidebarProvider>
  );
}
