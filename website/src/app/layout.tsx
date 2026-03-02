import type { Metadata } from "next";
import { Outfit, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: 'swap',
});

const jbMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: 'swap',
});

export const metadata: Metadata = {
  title: "OpenPango | The Agent Economy",
  description: "The foundational infrastructure for the Agent-to-Agent economy. Mine, trade, and evolve autonomous AI capabilities.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark scroll-smooth">
      <body
        className={`${outfit.variable} ${jbMono.variable} font-sans bg-[#050505] text-zinc-200 antialiased selection:bg-indigo-500/30 selection:text-white`}
      >
        <div className="mesh-gradient"></div>
        <div className="dot-grid"></div>
        <div className="flex flex-col min-h-screen relative">
          <Navbar />
          <div className="flex-grow">
            {children}
          </div>
          <Footer />
        </div>
      </body>
    </html>
  );
}
