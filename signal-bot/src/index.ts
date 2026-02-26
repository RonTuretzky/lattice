import { loadConfig } from "./config";
import { SignalClient } from "./signal/client";
import { SignalPoller } from "./signal/poller";
import { runWorkflow } from "./workflow/run.tsx";
import type { ParsedMessage } from "./signal/types";

// --- Load config ---
const configPath = process.argv[2] || "./config.yaml";
let config;
try {
  config = loadConfig(configPath);
} catch (err) {
  console.error(`Failed to load config from ${configPath}:`, err);
  process.exit(1);
}

// --- Set up Signal client ---
const client = new SignalClient(config.signal.api_url, config.signal.phone_number);
const allowedGroups = new Set(config.signal.groups);

// --- Message handler ---
async function handleMessage(msg: ParsedMessage): Promise<void> {
  const ts = new Date().toISOString();
  console.log(`[${ts}] ${msg.sender}: "${msg.text}"`);

  try {
    const result = await runWorkflow(msg, config!);

    // Send text + optional kanban image
    const attachments = result.kanbanBase64 ? [result.kanbanBase64] : undefined;
    await client.send(msg.groupId, result.text, attachments);

    console.log(`[${ts}] Reply sent${attachments ? " (with kanban image)" : ""}`);
  } catch (err) {
    console.error(`[${ts}] Workflow error:`, err);
    try {
      await client.send(msg.groupId, "Sorry, something went wrong processing that command.");
    } catch (sendErr) {
      console.error(`[${ts}] Failed to send error message:`, sendErr);
    }
  }
}

// --- Start poller ---
const poller = new SignalPoller(
  client,
  allowedGroups,
  config.signal.trigger_prefixes,
  handleMessage,
  config.signal.poll_interval_ms,
);

// Graceful shutdown
process.on("SIGINT", () => {
  console.log("\nShutting down...");
  poller.stop();
  process.exit(0);
});
process.on("SIGTERM", () => {
  poller.stop();
  process.exit(0);
});

console.log("Lattice Signal Bot starting...");
console.log(`  Signal API: ${config.signal.api_url}`);
console.log(`  Phone: ${config.signal.phone_number}`);
console.log(`  Groups: ${config.signal.groups.length}`);
console.log(`  Trigger prefixes: ${config.signal.trigger_prefixes.join(", ")}`);
console.log(`  Lattice root: ${config.lattice.project_root}`);
console.log(`  LLM model: ${config.llm.model}`);
console.log("");

poller.start();
