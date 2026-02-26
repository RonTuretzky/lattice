import { z } from "zod";

/** LLM interpretation of a natural language message into a Lattice command */
export const LatticeCommandSchema = z.object({
  understood: z
    .boolean()
    .describe("Whether the message maps to a Lattice command"),
  command: z
    .enum([
      "create",
      "list",
      "show",
      "status",
      "update",
      "comment",
      "assign",
      "complete",
      "next",
      "weather",
      "stats",
      "help",
      "none",
    ])
    .describe("The Lattice CLI command to execute"),
  positional: z
    .array(z.string())
    .describe("Positional arguments in order"),
  args: z
    .record(z.string())
    .describe("Named arguments as --flag value pairs"),
  flags: z
    .array(z.string())
    .describe("Boolean flags to include"),
  explanation: z
    .string()
    .describe("Brief explanation of what was understood"),
});

export type LatticeCommand = z.infer<typeof LatticeCommandSchema>;

/** Whether a command mutates state (triggers kanban image) */
export const WRITE_COMMANDS = new Set([
  "create",
  "status",
  "update",
  "assign",
  "complete",
  "comment",
  "next",
]);

/** Result from executing a Lattice CLI command */
export const ExecResultSchema = z.object({
  success: z.boolean(),
  command: z.string().describe("The Lattice command name"),
  commandString: z.string().describe("Full CLI command that was run"),
  rawOutput: z.string(),
  parsedOutput: z.any(),
  formattedMessage: z.string().describe("Human-readable message for Signal"),
});

export type ExecResult = z.infer<typeof ExecResultSchema>;
