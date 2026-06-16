import type { Metadata } from "next";
import "./globals.css";
import { Geist, Geist_Mono } from "next/font/google";
import React from "react";
import { NuqsAdapter } from "nuqs/adapters/next/app";

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist",
  display: "swap",
});

const geistMono = Geist_Mono({
  subsets: ["latin"],
  variable: "--font-geist-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Agent Chat",
  description: "Professional AI Agent Chat Interface",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geist.variable} ${geistMono.variable} dark antialiased`} style={{ fontFamily: "var(--font-geist), system-ui, sans-serif" }}>
        <NuqsAdapter>{children}</NuqsAdapter>
      </body>
    </html>
  );
}
