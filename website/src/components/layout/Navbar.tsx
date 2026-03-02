"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Github } from "lucide-react";
import { cn } from "@/lib/utils";

export function Navbar() {
  const pathname = usePathname();

  const navLinks = [
    { href: "/agents", label: "Agents" },
    { href: "/leaderboard", label: "Leaderboard" },
    { href: "/operator", label: "Operator" },
    { href: "/persona-builder", label: "Persona Builder" },
    { href: "/#mining", label: "Mining" },
    { href: "/#runtime", label: "Runtime" },
    { href: "/docs", label: "Docs" },
  ];

  return (
    <nav className="fixed top-0 w-full z-50 border-b border-white/10 bg-black/50 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 font-bold text-xl tracking-widest uppercase hover:opacity-80 transition-opacity">
          <span className="text-3xl">🦔</span> OPENPANGO
        </Link>
        <div className="hidden md:flex items-center gap-8 font-mono text-sm tracking-widest text-zinc-400 uppercase">
          {navLinks.map((link) => {
            const isActive = pathname === link.href;
            return (
              <Link
                key={link.label}
                href={link.href}
                className={cn(
                  "transition-colors hover:text-accent",
                  isActive ? "text-accent border-b border-accent/50" : "text-zinc-400"
                )}
              >
                {link.label}
              </Link>
            );
          })}
          <a
            href="https://github.com/openpango"
            target="_blank"
            rel="noopener noreferrer"
            className="border border-white/20 px-4 py-2 hover:border-accent hover:text-accent transition-colors flex items-center gap-2"
          >
            <Github className="w-4 h-4" /> GitHub
          </a>
        </div>
      </div>
    </nav>
  );
}
