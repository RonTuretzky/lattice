import type { SignalClient } from "./client";
import type {
  SignalEnvelope,
  ParsedMessage,
  ChatMessage,
  ChatHistory,
} from "./types";

export class SignalPoller {
  private running = false;
  /** Ring buffer of recent messages per group (groupId → messages[]) */
  private history = new Map<string, ChatMessage[]>();

  constructor(
    private client: SignalClient,
    private allowedGroups: Set<string>,
    private triggerPrefixes: string[],
    private onMessage: (history: ChatHistory) => Promise<void>,
    private intervalMs: number,
    private maxHistoryMessages: number = 50,
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

          const stripped = this.stripPrefix(msg.text);
          const isTriggered = stripped !== null;

          // Store every message in history (triggered or not)
          this.pushHistory(msg.groupId, {
            sender: msg.sender,
            text: msg.text,
            timestamp: msg.timestamp,
            isTriggered,
          });

          // Only dispatch workflow for triggered messages
          if (!isTriggered) continue;

          const triggeredMsg: ParsedMessage = {
            ...msg,
            text: stripped!.trim(),
          };
          if (!triggeredMsg.text) continue;

          const chatHistory: ChatHistory = {
            triggered: triggeredMsg,
            recentMessages: this.getHistory(msg.groupId),
          };

          await this.onMessage(chatHistory);
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

  /** Push a message into the group's ring buffer */
  private pushHistory(groupId: string, msg: ChatMessage): void {
    let buf = this.history.get(groupId);
    if (!buf) {
      buf = [];
      this.history.set(groupId, buf);
    }
    buf.push(msg);
    // Evict oldest when over limit
    while (buf.length > this.maxHistoryMessages) {
      buf.shift();
    }
  }

  /** Get a copy of the group's message history */
  private getHistory(groupId: string): ChatMessage[] {
    return [...(this.history.get(groupId) ?? [])];
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
