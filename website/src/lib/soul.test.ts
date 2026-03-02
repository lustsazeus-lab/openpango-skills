import { generateSoulMd, exportAsJson, exportAsYaml, defaultPersona, PersonaState } from '../lib/soul';

describe('soul generator', () => {
  it('generates valid SOUL.md', () => {
    const soul = generateSoulMd(defaultPersona);
    expect(soul).toContain('# SOUL.md - My Agent');
    expect(soul).toContain('## Core Truths');
    expect(soul).toContain('## Boundaries');
    expect(soul).toContain('## Vibe');
  });

  it('exports as valid JSON', () => {
    const json = exportAsJson(defaultPersona);
    const parsed = JSON.parse(json);
    expect(parsed.name).toBe('My Agent');
    expect(parsed.creature).toBe('AI assistant');
  });

  it('exports as valid YAML', () => {
    const yaml = exportAsYaml(defaultPersona);
    expect(yaml).toContain('persona:');
    expect(yaml).toContain('name: "My Agent"');
  });

  it('handles custom persona state', () => {
    const custom: PersonaState = {
      name: 'TestBot',
      creature: 'Robot',
      emoji: '🤖',
      avatar: '',
      coreTruths: ['Test truth 1', 'Test truth 2'],
      boundaries: ['Boundary 1'],
      tone: {
        vibe: 'Test vibe',
        communicationStyle: 'Test style',
      },
      allowedTools: ['tool1'],
      restrictedTools: ['tool2'],
    };
    const soul = generateSoulMd(custom);
    expect(soul).toContain('# SOUL.md - TestBot');
    expect(soul).toContain('Test truth 1');
    expect(soul).toContain('Boundary 1');
  });
});
