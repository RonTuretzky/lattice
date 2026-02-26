import {
  createSmithers,
  runWorkflow as smithersRun,
} from "smithers-orchestrator";
import type { Config } from "../config";
import type { ParsedMessage } from "../signal/types";
import {
  LatticeCommandSchema,
  ExecResultSchema,
  WRITE_COMMANDS,
} from "./schemas";
import { LatticeInterpreterAgent } from "./agent";
import { buildCommandString, executeLatticeCommand } from "./execute";
import { formatLatticeResult } from "../signal/formatter";
import { generateKanbanMermaid } from "../kanban/generate";
import { renderMermaidToBase64 } from "../kanban/render";

export interface WorkflowResult {
  /** Text message to send back to Signal */
  text: string;
  /** Base64-encoded PNG of kanban board (only for write commands) */
  kanbanBase64: string | null;
}

// Create Smithers instance with our schema registry.
// This sets up SQLite persistence for durable workflow state.
const { Workflow, Task, smithers, outputs } = createSmithers(
  {
    interpret: LatticeCommandSchema,
  },
  { dbPath: "./smithers.db" },
);

/**
 * Build a Smithers workflow definition for message interpretation.
 * The workflow has one agent task: Claude interprets the NL message
 * into a structured LatticeCommand via the Zod schema.
 */
function buildInterpretWorkflow(config: Config) {
  const agent = new LatticeInterpreterAgent(config.llm.model);

  return smithers((ctx) => (
    <Workflow name="lattice-signal-bot">
      <Task id="interpret" output={outputs.interpret} agent={agent}>
        {`Signal message from ${(ctx.input as any).sender}:\n\n"${(ctx.input as any).text}"\n\nInterpret this as a Lattice command.`}
      </Task>
    </Workflow>
  ));
}

/**
 * Run the full workflow for a single Signal message:
 * 1. Smithers workflow: Claude interprets NL → LatticeCommand (durable, schema-validated)
 * 2. Execute the Lattice CLI command
 * 3. If write command, generate kanban board PNG
 * 4. Return text + optional image
 */
export async function runWorkflow(
  msg: ParsedMessage,
  config: Config,
): Promise<WorkflowResult> {
  console.log(`[workflow] Processing: "${msg.text}" from ${msg.sender}`);

  // Step 1: Smithers-orchestrated interpretation
  const workflow = buildInterpretWorkflow(config);
  const result = await smithersRun(workflow, {
    input: {
      text: msg.text,
      sender: msg.sender,
      senderUuid: msg.senderUuid,
      groupId: msg.groupId,
      timestamp: String(msg.timestamp),
    },
  });

  if (result.status !== "finished") {
    console.error(
      `[workflow] Smithers run ${result.status}:`,
      (result as any).error,
    );
    return {
      text: "Sorry, I couldn't process that command.",
      kanbanBase64: null,
    };
  }

  // Extract the interpretation output row
  const rows = (result.output as any[]) ?? [];
  const cmd = rows[0];

  if (!cmd) {
    return {
      text: "Sorry, I couldn't interpret that message.",
      kanbanBase64: null,
    };
  }

  console.log(
    `[workflow] Interpreted: ${cmd.command} (understood=${cmd.understood})`,
  );

  // Not understood
  if (!cmd.understood || cmd.command === "none") {
    return {
      text:
        cmd.explanation ||
        config.bot.help_text ||
        "I didn't understand that. Try @lattice help",
      kanbanBase64: null,
    };
  }

  // Help
  if (cmd.command === "help") {
    return {
      text:
        config.bot.help_text ||
        [
          "Available commands:",
          "  create - Create a new task",
          "  list - List tasks (with filters)",
          "  show <id> - Show task details",
          "  status <id> <status> - Change status",
          "  assign <id> <actor> - Assign task",
          "  complete <id> - Mark as done",
          "  comment <id> - Add a comment",
          "  next - Pick next task",
          "  weather - Project health",
          "  stats - Project statistics",
        ].join("\n"),
      kanbanBase64: null,
    };
  }

  // Step 2: Execute Lattice CLI command
  const latticeConfig = {
    project_root: config.lattice.project_root,
    actor: config.lattice.actor,
  };
  const cmdStr = buildCommandString(cmd, latticeConfig);
  console.log(`[workflow] Executing: ${cmdStr}`);

  const execResult = executeLatticeCommand(cmdStr, latticeConfig);
  const formattedMessage = formatLatticeResult(cmd.command, execResult.parsed);

  // Step 3: Generate kanban image for write commands
  let kanbanBase64: string | null = null;
  if (WRITE_COMMANDS.has(cmd.command)) {
    console.log("[workflow] Generating kanban board image...");
    const mermaid = generateKanbanMermaid(config.lattice.project_root);
    if (mermaid) {
      kanbanBase64 = await renderMermaidToBase64(mermaid);
      if (kanbanBase64) {
        console.log("[workflow] Kanban image generated");
      } else {
        console.warn("[workflow] Failed to render kanban image");
      }
    }
  }

  return { text: formattedMessage, kanbanBase64 };
}
