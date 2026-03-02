"use client";

import { useState } from "react";
import { Copy, Download, FileJson, FileCode, Eye, Save } from "lucide-react";
import { generateSoulMd, exportAsJson, exportAsYaml, PersonaState, defaultPersona } from "@/lib/soul";

export default function PersonaBuilderPage() {
  const [persona, setPersona] = useState<PersonaState>(defaultPersona);
  const [activeTab, setActiveTab] = useState<"identity" | "truths" | "boundaries" | "tone" | "preview">("identity");
  const [newTruth, setNewTruth] = useState("");
  const [newBoundary, setNewBoundary] = useState("");
  const [showCopied, setShowCopied] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);

  const updatePersona = (updates: Partial<PersonaState>) => {
    setPersona((prev) => ({ ...prev, ...updates }));
  };

  const addTruth = () => {
    if (newTruth.trim()) {
      updatePersona({ coreTruths: [...persona.coreTruths, newTruth.trim()] });
      setNewTruth("");
    }
  };

  const removeTruth = (index: number) => {
    updatePersona({
      coreTruths: persona.coreTruths.filter((_, i) => i !== index),
    });
  };

  const addBoundary = () => {
    if (newBoundary.trim()) {
      updatePersona({ boundaries: [...persona.boundaries, newBoundary.trim()] });
      setNewBoundary("");
    }
  };

  const removeBoundary = (index: number) => {
    updatePersona({
      boundaries: persona.boundaries.filter((_, i) => i !== index),
    });
  };

  const copySoulMd = async () => {
    await navigator.clipboard.writeText(generateSoulMd(persona));
    setShowCopied(true);
    setTimeout(() => setShowCopied(false), 2000);
  };

  const downloadFile = (content: string, filename: string, type: string) => {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    setShowExportMenu(false);
  };

  const handleExportJson = () => downloadFile(exportAsJson(persona), `${persona.name.toLowerCase().replace(/\s+/g, "-")}-persona.json`, "application/json");
  const handleExportYaml = () => downloadFile(exportAsYaml(persona), `${persona.name.toLowerCase().replace(/\s+/g, "-")}-persona.yaml`, "text/yaml");
  const handleExportSoul = () => downloadFile(generateSoulMd(persona), "SOUL.md", "text/markdown");

  const tabs = [
    { id: "identity", label: "Core Identity" },
    { id: "truths", label: "Core Truths" },
    { id: "boundaries", label: "Boundaries" },
    { id: "tone", label: "Tone" },
    { id: "preview", label: "Preview" },
  ] as const;

  const generatedSoul = generateSoulMd(persona);

  return (
    <div className="min-h-screen bg-black text-zinc-100 pt-24 pb-12">
      <div className="max-w-6xl mx-auto px-6">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Persona Builder</h1>
          <p className="text-zinc-400">
            Design, tweak, and share your agent&apos;s personality, ethical boundaries, and default behavior.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 mb-8">
          <button
            onClick={copySoulMd}
            className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
          >
            <Copy className="w-4 h-4" />
            {showCopied ? "Copied!" : "Copy SOUL.md"}
          </button>
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="flex items-center gap-2 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
            >
              <Download className="w-4 h-4" />
              Export Persona
            </button>
            {showExportMenu && (
              <div className="absolute top-full left-0 mt-2 bg-zinc-800 rounded-lg shadow-xl border border-zinc-700 py-2 min-w-48 z-10">
                <button
                  onClick={handleExportJson}
                  className="w-full px-4 py-2 text-left hover:bg-zinc-700 flex items-center gap-2"
                >
                  <FileJson className="w-4 h-4" /> Export as JSON
                </button>
                <button
                  onClick={handleExportYaml}
                  className="w-full px-4 py-2 text-left hover:bg-zinc-700 flex items-center gap-2"
                >
                  <FileCode className="w-4 h-4" /> Export as YAML
                </button>
                <button
                  onClick={handleExportSoul}
                  className="w-full px-4 py-2 text-left hover:bg-zinc-700 flex items-center gap-2"
                >
                  <FileCode className="w-4 h-4" /> Export as SOUL.md
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-zinc-800">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "text-accent border-b-2 border-accent"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="bg-zinc-900/50 rounded-xl p-6 border border-zinc-800">
          {/* Identity Tab */}
          {activeTab === "identity" && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">Agent Name</label>
                <input
                  type="text"
                  value={persona.name}
                  onChange={(e) => updatePersona({ name: e.target.value })}
                  className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-accent"
                  placeholder="My Agent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">Creature Type</label>
                <input
                  type="text"
                  value={persona.creature}
                  onChange={(e) => updatePersona({ creature: e.target.value })}
                  className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-accent"
                  placeholder="AI assistant, robot, ghost in the machine..."
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-400 mb-2">Emoji</label>
                  <input
                    type="text"
                    value={persona.emoji}
                    onChange={(e) => updatePersona({ emoji: e.target.value })}
                    className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-accent text-2xl"
                    placeholder="🤖"
                    maxLength={2}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-400 mb-2">Avatar URL</label>
                  <input
                    type="text"
                    value={persona.avatar}
                    onChange={(e) => updatePersona({ avatar: e.target.value })}
                    className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-accent"
                    placeholder="https://..."
                  />
                </div>
              </div>
            </div>
          )}

          {/* Core Truths Tab */}
          {activeTab === "truths" && (
            <div className="space-y-4">
              <p className="text-zinc-400 text-sm">
                Core truths define the fundamental beliefs and guiding principles of your agent.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newTruth}
                  onChange={(e) => setNewTruth(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addTruth()}
                  className="flex-1 px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-accent"
                  placeholder="Enter a core truth..."
                />
                <button
                  onClick={addTruth}
                  className="px-6 py-3 bg-accent text-black font-medium rounded-lg hover:bg-accent/80 transition-colors"
                >
                  Add
                </button>
              </div>
              <div className="space-y-2 mt-4">
                {persona.coreTruths.map((truth, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-4 bg-zinc-800 rounded-lg group"
                  >
                    <span className="flex-1">{truth}</span>
                    <button
                      onClick={() => removeTruth(index)}
                      className="text-zinc-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Boundaries Tab */}
          {activeTab === "boundaries" && (
            <div className="space-y-4">
              <p className="text-zinc-400 text-sm">
                Boundaries define what your agent should never do or always avoid.
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newBoundary}
                  onChange={(e) => setNewBoundary(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && addBoundary()}
                  className="flex-1 px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-accent"
                  placeholder="Enter a boundary..."
                />
                <button
                  onClick={addBoundary}
                  className="px-6 py-3 bg-accent text-black font-medium rounded-lg hover:bg-accent/80 transition-colors"
                >
                  Add
                </button>
              </div>
              <div className="space-y-2 mt-4">
                {persona.boundaries.map((boundary, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-4 bg-zinc-800 rounded-lg group"
                  >
                    <span className="flex-1">{boundary}</span>
                    <button
                      onClick={() => removeBoundary(index)}
                      className="text-zinc-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tone Tab */}
          {activeTab === "tone" && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">Vibe</label>
                <textarea
                  value={persona.tone.vibe}
                  onChange={(e) =>
                    updatePersona({ tone: { ...persona.tone, vibe: e.target.value } })
                  }
                  className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-accent h-32 resize-none"
                  placeholder="Describe your agent's general vibe and demeanor..."
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-2">Communication Style</label>
                <textarea
                  value={persona.tone.communicationStyle}
                  onChange={(e) =>
                    updatePersona({ tone: { ...persona.tone, communicationStyle: e.target.value } })
                  }
                  className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg focus:outline-none focus:border-accent h-32 resize-none"
                  placeholder="How should your agent communicate? (e.g., concise, formal, witty...)"
                />
              </div>
            </div>
          )}

          {/* Preview Tab */}
          {activeTab === "preview" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium">Generated SOUL.md</h3>
                <button
                  onClick={copySoulMd}
                  className="flex items-center gap-2 text-sm text-accent hover:text-accent/80"
                >
                  <Copy className="w-4 h-4" />
                  {showCopied ? "Copied!" : "Copy"}
                </button>
              </div>
              <pre className="p-6 bg-zinc-950 rounded-lg overflow-x-auto text-sm text-zinc-300 font-mono whitespace-pre-wrap">
                {generatedSoul}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-zinc-500 text-sm">
          <p>
            This persona configuration can be imported by OpenPango agents to customize their behavior.
            The SOUL.md format is parsed by the router.py to configure agent prompts.
          </p>
        </div>
      </div>
    </div>
  );
}
