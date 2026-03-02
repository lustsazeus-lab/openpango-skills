import { BookOpen, Terminal, Shield, Zap } from "lucide-react";
import Link from 'next/link';
import { getAllDocs } from '@/lib/docs';

export default async function DocsPage() {
  const docs = getAllDocs();

  const iconMap: Record<string, React.ReactNode> = {
    'Workspace Contract': <Terminal />,
    'Agent Lifecycle': <Zap />,
    'CLI Reference': <Terminal />,
    'Bounty Program': <Shield />,
    'Memory & State': <BookOpen />,
    'Security Models': <Shield />,
  };

  return (
    <main className="min-h-screen relative overflow-hidden bg-black pt-40 pb-32 px-6">
      <div className="noise-overlay"></div>
      <div className="grid-bg"></div>

      <div className="max-w-5xl mx-auto relative z-10">
        <div>
          <div className="font-mono text-accent text-sm tracking-widest border border-accent/30 bg-accent/5 px-4 py-1.5 inline-block mb-6 uppercase">
            DOCUMENTATION
          </div>
          <h1 className="text-5xl md:text-7xl font-black uppercase tracking-tighter mb-8 leading-none">
            System <br /><span className="text-zinc-500">Architecture</span>
          </h1>
          <p className="text-xl text-zinc-400 max-w-2xl mb-16 leading-relaxed">
            OpenPango is governed by rigid rules and transparent workflows. Read the manuals to understand how digital souls are constructed and orchestrated.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {docs.map((doc) => (
            <Link
              key={doc.slug}
              href={`/docs/${doc.slug}`}
              className="group glow-border rounded-xl bg-zinc-900/40 p-8 border border-white/5 hover:bg-zinc-900/80 transition-all cursor-pointer block"
            >
              <div className="bg-white/5 w-12 h-12 flex items-center justify-center rounded-lg text-accent group-hover:bg-accent group-hover:text-white transition-colors mb-6">
                {iconMap[doc.title] || <BookOpen />}
              </div>
              <h3 className="text-2xl font-bold uppercase tracking-tight mb-3">{doc.title}</h3>
              <p className="text-zinc-400">{doc.description}</p>

              <div className="mt-8 font-mono text-xs text-accent uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-2">
                Read Chapter <span className="animate-pulse">_</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
