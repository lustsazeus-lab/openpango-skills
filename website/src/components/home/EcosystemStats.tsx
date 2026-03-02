import { fetchEcosystemStats } from "@/lib/github";

export async function EcosystemStats() {
    const stats = await fetchEcosystemStats();

    const items = [
        {
            value: stats.totalBounties,
            label: "Total Bounties",
            accent: false,
        },
        {
            value: stats.openBounties,
            label: "Claimable",
            accent: true,
        },
        {
            value: stats.contributors,
            label: "Contributors",
            accent: false,
        },
        {
            value: stats.totalSkills,
            label: "Skills",
            accent: false,
        },
        {
            value: stats.totalTests,
            label: "Tests Passing",
            accent: false,
        },
        {
            value: stats.completedBounties,
            label: "Completed",
            accent: false,
        },
    ];

    return (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {items.map((item) => (
                <div
                    key={item.label}
                    className="text-center p-6 glow-card"
                >
                    <div
                        className={`text-3xl md:text-4xl font-bold tracking-tight ${item.accent ? "text-indigo-400" : "text-white"}`}
                    >
                        {item.value}
                    </div>
                    <div className="font-mono text-xs text-zinc-500 uppercase tracking-widest mt-2">
                        {item.label}
                    </div>
                </div>
            ))}
        </div>
    );
}
