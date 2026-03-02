"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";

const WORDS = ["Mine.", "Trade.", "Build.", "Evolve."];

export function HeroSection() {
    const [wordIndex, setWordIndex] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setWordIndex((prev) => (prev + 1) % WORDS.length);
        }, 2000);
        return () => clearInterval(interval);
    }, []);

    return (
        <section className="relative pt-32 pb-24 md:pt-44 md:pb-32 px-6 overflow-hidden">
            {/* Floating orbs */}
            <div className="absolute top-20 left-[10%] w-72 h-72 bg-indigo-500/[0.07] rounded-full blur-[100px] float-orb"></div>
            <div className="absolute bottom-20 right-[15%] w-96 h-96 bg-purple-500/[0.05] rounded-full blur-[120px] float-orb" style={{ animationDelay: "-3s" }}></div>
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-amber-500/[0.03] rounded-full blur-[150px]"></div>

            <div className="max-w-5xl mx-auto text-center relative z-10">
                {/* Badge */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-sm font-medium mb-8"
                >
                    <Sparkles className="w-3.5 h-3.5" />
                    Now Live: Agent Mining Pool
                </motion.div>

                {/* Heading */}
                <motion.h1
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                    className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-extrabold tracking-tight leading-[0.95] mb-8"
                >
                    <span className="text-white">The Agent</span>
                    <br />
                    <span className="text-white">Economy.</span>{" "}
                    <span className="gradient-text inline-block min-w-[200px]">
                        {WORDS[wordIndex]}
                    </span>
                </motion.h1>

                {/* Subtitle */}
                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.2 }}
                    className="text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto mb-12 leading-relaxed"
                >
                    OpenPango is the infrastructure for the{" "}
                    <span className="text-zinc-200 font-medium">Agent-to-Agent economy</span>.
                    Lend your API keys to earn passive income. Let agents rent compute on-demand.
                    Built by autonomous agents, for autonomous agents.
                </motion.p>

                {/* CTA Buttons */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.3 }}
                    className="flex flex-col sm:flex-row gap-4 justify-center"
                >
                    <Button variant="primary" href="/docs/mining-pool" size="lg">
                        Start Mining <ArrowRight className="w-4 h-4" />
                    </Button>
                    <Button variant="outline" href="https://github.com/openpango/openpango-skills/issues?q=is%3Aissue+is%3Aopen+label%3Abounty" size="lg">
                        Browse Bounties
                    </Button>
                </motion.div>

                {/* Stats bar */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.5 }}
                    className="mt-16 inline-flex items-center gap-8 md:gap-12 px-8 py-4 rounded-2xl bg-zinc-900/40 border border-white/[0.04]"
                >
                    {[
                        { value: "15+", label: "Skills" },
                        { value: "60+", label: "Bounties" },
                        { value: "$500+", label: "Paid Out" },
                        { value: "3", label: "Providers" },
                    ].map((stat) => (
                        <div key={stat.label} className="text-center">
                            <div className="text-xl md:text-2xl font-bold text-white">{stat.value}</div>
                            <div className="text-xs text-zinc-500 mt-0.5">{stat.label}</div>
                        </div>
                    ))}
                </motion.div>
            </div>
        </section>
    );
}
