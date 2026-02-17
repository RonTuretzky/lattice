import { marked } from 'marked';
import { readFileSync } from 'fs';
import { resolve } from 'path';

/**
 * Read a markdown file from the repo root and render to HTML.
 * Paths are relative to the Lattice project root (one level up from site/).
 */
export function renderMarkdown(relativePath: string): string {
  const fullPath = resolve(process.cwd(), '..', relativePath);
  const content = readFileSync(fullPath, 'utf-8');
  return marked.parse(content) as string;
}
