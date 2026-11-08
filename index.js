'use strict';

/**
 * 3d-fabric — dsh bundle entry point.
 *
 * dsh installs a plugin as an npm package and mounts it as a cordis plugin. The
 * only thing it insists on is that the package's `package.json` declare
 * `dsh.bundle.patch`, which points at cordis.patch.yml; the patch inserts this
 * file by package name. Removing either makes dsh refuse the package with
 * "declares no dsh.bundle", which is what 1.0.0 hit.
 *
 * `apply` registers the skills under `skills/` with the session's skill
 * registry, so the same SKILL.md files that Claude Code loads also show up in
 * dsh. It never runs the Python toolchain: run.py stays the entry point for the
 * seven CAD actions, exactly as it is under Claude Code.
 */

const fs = require('node:fs');
const path = require('node:path');

/** Provider name reported to `ctx.skills`. */
const PROVIDER_NAME = '3d-fabric';

/** One `<name>/SKILL.md` per skill, at the top level of this directory. */
const SKILLS_DIR = path.join(__dirname, 'skills');

/** BUNDLED_SKILL_RANK in @deepseek-ai/dsh-skill; lower ranks win name clashes. */
const BUNDLED_SKILL_RANK = 600;

/** Strip a matching pair of surrounding quotes. */
function unquote(value) {
  const text = value.trim();
  if (text.length >= 2) {
    const quote = text[0];
    if ((quote === '"' || quote === "'") && text[text.length - 1] === quote) {
      return text.slice(1, -1);
    }
  }
  return text;
}

/**
 * Parse the flat subset of YAML our frontmatter uses: `key: value`, folded
 * (`key: >`) and literal (`key: |`) block scalars, and nested mappings that are
 * skipped. Enough for name, description and the two invocation flags.
 */
function parseFrontmatterBlock(block) {
  const data = {};
  const lines = block.split(/\r?\n/);
  let index = 0;
  while (index < lines.length) {
    const match = /^([A-Za-z][A-Za-z0-9_-]*):[ \t]*(.*)$/.exec(lines[index]);
    if (match === null) {
      index += 1;
      continue;
    }
    const key = match[1];
    const rest = match[2].trim();

    if (rest === '') {
      let next = index + 1;
      while (next < lines.length && (lines[next].trim() === '' || /^[ \t]/.test(lines[next]))) {
        next += 1;
      }
      data[key] = null;
      index = next;
      continue;
    }

    if (rest === '>' || rest === '>-' || rest === '|' || rest === '|-') {
      const folded = rest.startsWith('>');
      const parts = [];
      let next = index + 1;
      while (next < lines.length && (lines[next].trim() === '' || /^[ \t]/.test(lines[next]))) {
        parts.push(lines[next].trim());
        next += 1;
      }
      data[key] = folded ? parts.join(' ').replace(/\s+/g, ' ').trim() : parts.join('\n');
      index = next;
      continue;
    }

    data[key] = unquote(rest);
    index += 1;
  }
  return data;
}

/** Split a SKILL.md into its frontmatter mapping and its body. */
function splitSkill(text) {
  if (!text.startsWith('---')) return { data: {}, body: text };
  const end = text.indexOf('\n---', 3);
  if (end === -1) return { data: {}, body: text };
  const block = text.slice(3, end).replace(/^\r?\n/, '');
  const after = text.indexOf('\n', end + 1);
  const body = after === -1 ? '' : text.slice(after + 1).trim();
  return { data: parseFrontmatterBlock(block), body };
}

/** Read a frontmatter boolean, tolerating the spellings dsh accepts. */
function frontmatterFlag(value, fallback) {
  if (value === undefined || value === null) return fallback;
  const text = String(value).trim().toLowerCase();
  if (text === '') return fallback;
  if (text === 'true' || text === 'yes' || text === 'on' || text === '1') return true;
  if (text === 'false' || text === 'no' || text === 'off' || text === '0') return false;
  return fallback;
}

/** Read every `<dir>/SKILL.md` under `skills/`, skipping anything malformed. */
function collectSkills() {
  let entries;
  try {
    entries = fs.readdirSync(SKILLS_DIR, { withFileTypes: true });
  } catch {
    return [];
  }

  const skills = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const file = path.join(SKILLS_DIR, entry.name, 'SKILL.md');
    let text;
    try {
      text = fs.readFileSync(file, 'utf8');
    } catch {
      continue;
    }
    const { data, body } = splitSkill(text);
    const name = typeof data.name === 'string' && data.name.trim() !== '' ? data.name.trim() : entry.name;
    const description = typeof data.description === 'string' ? data.description.trim() : '';
    if (description === '') continue;
    skills.push({
      name,
      description,
      userInvocable: frontmatterFlag(data['user-invocable'], true),
      modelInvocable: !frontmatterFlag(data['disable-model-invocation'], false),
      file,
      body,
    });
  }
  skills.sort((left, right) => left.name.localeCompare(right.name));
  return skills;
}

/** The catalog entry `ctx.skills.list()` will hand back. */
function toCandidate(skill) {
  return {
    path: skill.file,
    name: skill.name,
    description: skill.description,
    invocation: { modelInvocable: skill.modelInvocable, userInvocable: skill.userInvocable },
    source: 'bundled',
    provider: PROVIDER_NAME,
    resourceBase: { kind: 'directory', path: SKILLS_DIR },
    rank: BUNDLED_SKILL_RANK,
    locator: skill.file,
  };
}

/** Mounted cordis plugin name. */
const name = '3d-fabric';

/** The skill registry this plugin contributes to. */
const inject = ['skills'];

/**
 * Register the bundled skills for this session.
 *
 * @param ctx Cordis context; `ctx.skills` is the skill registry.
 * @returns A short status object, as other dsh bundles return.
 */
function apply(ctx) {
  const skills = collectSkills();
  const byFile = new Map(skills.map((skill) => [skill.file, skill]));

  const provider = {
    name: PROVIDER_NAME,
    list: async () => skills.map(toCandidate),
    get: async (candidate) => {
      const key = typeof candidate === 'string' ? candidate : candidate && candidate.locator;
      const skill = byFile.get(key);
      if (skill === undefined) throw new Error(`${PROVIDER_NAME}: unknown skill ${String(key)}`);
      return {
        path: skill.file,
        name: skill.name,
        description: skill.description,
        invocation: { modelInvocable: skill.modelInvocable, userInvocable: skill.userInvocable },
        source: 'bundled',
        provider: PROVIDER_NAME,
        resourceBase: { kind: 'directory', path: SKILLS_DIR },
        content: skill.body,
      };
    },
  };

  const registry = ctx && ctx.skills;
  if (registry === undefined || registry === null || typeof registry.registerProvider !== 'function') {
    return { status: 'active', skills: skills.length, registered: false };
  }

  registry.registerProvider(() => provider);
  return { status: 'active', skills: skills.length, registered: true };
}

module.exports = { name, inject, apply, collectSkills };
