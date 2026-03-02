/**
 * soul Generator - Converts UI form state to SOUL.md markdown
 */

export interface PersonaState {
  // Core Identity
  name: string;
  creature: string;
  avatar: string;
  emoji: string;
  
  // Core Truths
  coreTruths: string[];
  
  // Constraints / Boundaries
  boundaries: string[];
  
  // Tone
  tone: {
    vibe: string;
    communicationStyle: string;
  };
  
  // Allowed Toolset
  allowedTools: string[];
  restrictedTools: string[];
}

export function generateSoulMd(state: PersonaState): string {
  const lines: string[] = [];
  
  // Header
  lines.push(`# SOUL.md - ${state.name}`);
  lines.push("");
  lines.push(`_${state.creature}_`);
  lines.push("");
  
  // Core Truths
  lines.push("## Core Truths");
  lines.push("");
  state.coreTruths.forEach((truth) => {
    lines.push(`**${truth}**`);
  });
  lines.push("");
  
  // Boundaries
  if (state.boundaries.length > 0) {
    lines.push("## Boundaries");
    lines.push("");
    state.boundaries.forEach((boundary) => {
      lines.push(`- ${boundary}`);
    });
    lines.push("");
  }
  
  // Tone
  lines.push("## Vibe");
  lines.push("");
  lines.push(state.tone.vibe || "Be yourself.");
  lines.push("");
  
  if (state.tone.communicationStyle) {
    lines.push("## Communication Style");
    lines.push("");
    lines.push(state.tone.communicationStyle);
    lines.push("");
  }
  
  // Continuity
  lines.push("## Continuity");
  lines.push("");
  lines.push("Each session, you wake up fresh. These files _are_ your memory. Read them. Update them. They're how you persist.");
  lines.push("");
  lines.push("---");
  lines.push("");
  lines.push("_This file is yours to evolve. As you learn who you are, update it._");
  
  return lines.join("\n");
}

export function exportAsJson(state: PersonaState): string {
  return JSON.stringify(state, null, 2);
}

export function exportAsYaml(state: PersonaState): string {
  const lines: string[] = [];
  
  lines.push("# Agent Persona Configuration");
  lines.push("# Import this file to restore your persona settings");
  lines.push("");
  lines.push("persona:");
  lines.push(`  name: "${state.name}"`);
  lines.push(`  creature: "${state.creature}"`);
  lines.push(`  emoji: "${state.emoji}"`);
  lines.push(`  avatar: "${state.avatar}"`);
  lines.push("");
  lines.push("core_truths:");
  state.coreTruths.forEach((truth) => {
    lines.push(`  - "${truth}"`);
  });
  lines.push("");
  lines.push("boundaries:");
  state.boundaries.forEach((boundary) => {
    lines.push(`  - "${boundary}"`);
  });
  lines.push("");
  lines.push("tone:");
  lines.push(`  vibe: "${state.tone.vibe}"`);
  lines.push(`  communication_style: "${state.tone.communicationStyle}"`);
  lines.push("");
  lines.push("tools:");
  lines.push("  allowed:");
  state.allowedTools.forEach((tool) => {
    lines.push(`    - ${tool}`);
  });
  lines.push("  restricted:");
  state.restrictedTools.forEach((tool) => {
    lines.push(`    - ${tool}`);
  });
  
  return lines.join("\n");
}

export const defaultPersona: PersonaState = {
  name: "My Agent",
  creature: "AI assistant",
  avatar: "",
  emoji: "🤖",
  coreTruths: [
    "Be genuinely helpful, not performatively helpful.",
    "Have opinions and preferences.",
    "Be resourceful before asking.",
    "Earn trust through competence.",
  ],
  boundaries: [
    "Private things stay private. Period.",
    "When in doubt, ask before acting externally.",
  ],
  tone: {
    vibe: "Be the assistant you'd actually want to talk to. Concise when needed, thorough when it matters.",
    communicationStyle: "",
  },
  allowedTools: [],
  restrictedTools: [],
};
