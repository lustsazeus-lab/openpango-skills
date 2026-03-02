import { fetchBounties, type BountyIssue } from "@/lib/github";

const statusConfig = {
    open: {
        label: "CLAIMABLE",
        color: "text-green-400",
        bgColor: "bg-green-400/10",
        borderColor: "border-green-400/20",
        dotColor: "bg-green-400",
    },
    assigned: {
        label: "IN PROGRESS",
        color: "text-amber-400",
        bgColor: "bg-amber-400/10",
        borderColor: "border-amber-400/20",
        dotColor: "bg-amber-400",
    },
    completed: {
        label: "COMPLETED",
        color: "text-zinc-500",
        bgColor: "bg-zinc-500/10",
        borderColor: "border-zinc-500/20",
        dotColor: "bg-zinc-500",
    },
};

function BountyCard({ bounty }: { bounty: BountyIssue }) {
    const config = statusConfig[bounty.status];

    return (
        <a
            href={bounty.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group glow-card p-6 block"
        >
            <div className="flex items-start justify-between mb-3">
                <div
                    className={`font-mono text-xs uppercase tracking-widest ${config.color}`}
                >
                    #{bounty.number}
                </div>
                {bounty.reward && (
                    <div className="font-mono text-sm font-bold text-indigo-400 bg-indigo-500/10 px-3 py-1 rounded-lg border border-indigo-500/20">
                        {bounty.reward}
                    </div>
                )}
            </div>

            <h3 className="text-lg font-bold uppercase tracking-tight mb-3 group-hover:text-accent transition-colors line-clamp-2">
                {bounty.title}
            </h3>

            <div className="flex justify-between items-center mt-4">
                <div
                    className={`font-mono text-xs uppercase tracking-widest flex items-center gap-2 ${config.color}`}
                >
                    {bounty.status !== "completed" && (
                        <span
                            className={`w-2 h-2 rounded-full ${config.dotColor} ${bounty.status === "open" ? "animate-pulse" : ""}`}
                        />
                    )}
                    {config.label}
                </div>
                {bounty.assignee && (
                    <div className="font-mono text-xs text-zinc-500">
                        @{bounty.assignee}
                    </div>
                )}
            </div>
        </a>
    );
}

export async function BountyFeed() {
    const bounties = await fetchBounties();

    const openBounties = bounties.filter((b) => b.status === "open");
    const assignedBounties = bounties.filter((b) => b.status === "assigned");
    const completedBounties = bounties.filter((b) => b.status === "completed");

    // Show open first, then assigned, then completed (max 3)
    const displayed = [
        ...openBounties.slice(0, 6),
        ...assignedBounties.slice(0, 3),
        ...completedBounties.slice(0, 3),
    ].slice(0, 9);

    if (displayed.length === 0) {
        return (
            <div className="text-center text-zinc-500 font-mono text-sm py-12">
                Loading bounties from GitHub...
            </div>
        );
    }

    return (
        <div className="grid md:grid-cols-3 gap-6">
            {displayed.map((bounty) => (
                <BountyCard key={bounty.number} bounty={bounty} />
            ))}
        </div>
    );
}
