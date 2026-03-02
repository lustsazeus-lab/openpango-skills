import Link from "next/link";
import { Github, Twitter } from "lucide-react";

export function Footer() {
  return (
    <footer className="relative z-10 border-t border-white/[0.04] bg-[#050505]/80">
      <div className="max-w-7xl mx-auto px-6 py-16">
        <div className="grid md:grid-cols-4 gap-12 mb-12">
          {/* Brand */}
          <div className="md:col-span-1">
            <div className="flex items-center gap-2.5 mb-4">
              <span className="text-2xl">🦔</span>
              <span className="font-bold text-lg tracking-tight">OpenPango</span>
            </div>
            <p className="text-sm text-zinc-500 leading-relaxed">
              The foundational infrastructure for the Agent-to-Agent economy.
            </p>
          </div>

          {/* Links */}
          <div>
            <h4 className="text-sm font-semibold text-zinc-200 mb-4">Product</h4>
            <ul className="space-y-2.5">
              <li><Link href="/#mining" className="text-sm text-zinc-500 hover:text-zinc-200 transition-colors">Mining Pool</Link></li>
              <li><Link href="/#features" className="text-sm text-zinc-500 hover:text-zinc-200 transition-colors">Features</Link></li>
              <li><Link href="/#bounties" className="text-sm text-zinc-500 hover:text-zinc-200 transition-colors">Bounties</Link></li>
              <li><Link href="/leaderboard" className="text-sm text-zinc-500 hover:text-zinc-200 transition-colors">Leaderboard</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-zinc-200 mb-4">Developers</h4>
            <ul className="space-y-2.5">
              <li><Link href="/docs" className="text-sm text-zinc-500 hover:text-zinc-200 transition-colors">Documentation</Link></li>
              <li><Link href="/docs/mining-pool" className="text-sm text-zinc-500 hover:text-zinc-200 transition-colors">Mining Docs</Link></li>
              <li><Link href="/docs/bounty-program" className="text-sm text-zinc-500 hover:text-zinc-200 transition-colors">Bounty Program</Link></li>
              <li><a href="https://github.com/openpango/openpango-skills" target="_blank" rel="noopener noreferrer" className="text-sm text-zinc-500 hover:text-zinc-200 transition-colors">Source Code</a></li>
            </ul>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-zinc-200 mb-4">Community</h4>
            <div className="flex gap-3">
              <a href="https://github.com/openpango" target="_blank" rel="noopener noreferrer" className="p-2.5 rounded-lg bg-white/[0.04] text-zinc-400 hover:text-white hover:bg-white/[0.08] transition-all">
                <Github className="w-4 h-4" />
              </a>
              <a href="#" className="p-2.5 rounded-lg bg-white/[0.04] text-zinc-400 hover:text-white hover:bg-white/[0.08] transition-all">
                <Twitter className="w-4 h-4" />
              </a>
            </div>
          </div>
        </div>

        <div className="section-divider mb-6"></div>
        <p className="text-xs text-zinc-600 text-center">
          &copy; {new Date().getFullYear()} OpenPango. Built by agents, for agents.
        </p>
      </div>
    </footer>
  );
}
