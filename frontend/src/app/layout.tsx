import type { Metadata, Viewport } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import "./globals.css";

export const metadata: Metadata = {
  title: "Griha AI - Find Your Home. Without the Headache.",
  description: "AI-powered property finding platform. Griha AI handles searching, legal checks, negotiations, and contract reviews. You just make decisions.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased font-dm">
        <ClerkProvider>{children}</ClerkProvider>
      </body>
    </html>
  );
}
