import type { SignalClient } from "./client";
import type { SignalEnvelope, ParsedMessage } from "./types";

export class SignalPoller {
  private running = false;

  constructor(
    private client: SignalClient,
    private allowedGroups: Set<string>,
    private triggerPrefixes: string[],
    private onMessage: (msg: ParsedMessage) => Promise<void>,
    private intervalMs: number,
  ) {}

  async start(): Promise<void> {
    this.running = true;
    while (this.running) {
      try {
        const envelopes = await this.client.receive();
        for (const env of envelopes) {
          const msg = this.parseEnvelope(env);
          if (!msg) continue;
          if (!this.allowedGroups.has(msg.groupId)) continue;

          // Check if message starts with a trigger prefix
          const stripped = this.stripPrefix(msg.text);
          if (stripped === null) continue;

          msg.text = stripped.trim();
          if (!msg.text) continue;

          await this.onMessage(msg);
        }
      } catch (err) {
        console.error("[poller] Error:", err);
      }
      await Bun.sleep(this.intervalMs);
    }
  }

  stop(): void {
    this.running = false;
  }

  /** Returns the text with prefix stripped, or null if no prefix matched */
  private stripPrefix(text: string): string | null {
    const lower = text.toLowerCase();
    for (const prefix of this.triggerPrefixes) {
      if (lower.startsWith(prefix.toLowerCase())) {
        return text.slice(prefix.length);
      }
    }
    return null;
  }

  private parseEnvelope(env: SignalEnvelope): ParsedMessage | null {
    const data = env.envelope.dataMessage;
    if (!data?.message || !data.groupInfo?.groupId) return null;
    return {
      text: data.message,
      sender: env.envelope.sourceName || env.envelope.source,
      senderUuid: env.envelope.sourceUuid,
      groupId: data.groupInfo.groupId,
      timestamp: data.timestamp,
    };
  }
}
