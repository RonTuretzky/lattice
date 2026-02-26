import { readFileSync } from "node:fs";
import { z } from "zod";
import { parse as parseYaml } from "yaml";

const ConfigSchema = z.object({
  signal: z.object({
    api_url: z.string().url(),
    phone_number: z.string().startsWith("+"),
    poll_interval_ms: z.number().default(1000),
    groups: z.array(z.string()).min(1),
    trigger_prefixes: z.array(z.string()).default(["@lattice", "/lat"]),
  }),
  lattice: z.object({
    project_root: z.string(),
    actor: z.string().regex(/^[a-z]+:.+$/, "Actor must be prefix:identifier"),
  }),
  llm: z.object({
    model: z.string().default("claude-sonnet-4-5-20250929"),
  }),
  bot: z.object({
    name: z.string().default("LatticeBot"),
    help_text: z.string().optional(),
  }),
});

export type Config = z.infer<typeof ConfigSchema>;

export function loadConfig(path: string): Config {
  const raw = readFileSync(path, "utf-8");
  const parsed = parseYaml(raw);
  return ConfigSchema.parse(parsed);
}
