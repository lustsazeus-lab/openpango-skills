"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Github, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

export function Navbar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const navLinks = [
    { href: "/#mining", label: "Mining" },
    { href: "/#features", label: "Features" },
    { href: "/#bounties", label: "Bounties" },
    { href: "/docs", label: "Docs" },
    { href: "/leaderboard", label: "Leaderboard" },
  ];

  return (
    <nav className="fixed top-0 w-full z-50 bg-[#050505]/70 backdrop-blur-xl border-b border-white/[0.04]">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5 hover:opacity-80 transition-opacity">
          <span className="text-2xl">🦔</span>
          <span className="font-bold text-lg tracking-tight">OpenPango</span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-1">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.label}
                href={link.href}
                className={cn(
                  "px-3.5 py-2 rounded-lg text-sm font-medium transition-all",
                  isActive
                    ? "text-indigo-400 bg-indigo-500/10"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04]"
                )}
              >
                {link.label}
              </Link>
            );
          })}
          <div className="w-px h-6 bg-white/10 mx-2"></div>
          <a
            href="https://github.com/openpango"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-all"
          >
            <Github className="w-4 h-4" /> GitHub
          </a>
        </div>

        {/* Mobile hamburger */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden text-zinc-400 hover:text-white transition-colors p-2"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t border-white/[0.04] bg-[#050505]/95 backdrop-blur-xl px-6 py-4 space-y-1">
          {navLinks.map((link) => (
            <Link
              key={link.label}
              href={link.href}
              onClick={() => setMobileOpen(false)}
              className="block px-3 py-2.5 rounded-lg text-sm font-medium text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-all"
            >
              {link.label}
            </Link>
          ))}
          <a
            href="https://github.com/openpango"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm font-medium text-zinc-400 hover:text-zinc-200 hover:bg-white/[0.04] transition-all"
          >
            <Github className="w-4 h-4" /> GitHub
          </a>
        </div>
      )}
    </nav>
  );
}
