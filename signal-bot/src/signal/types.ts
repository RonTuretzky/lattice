/** Envelope returned by signal-cli-rest-api GET /v1/receive/{number} */
export interface SignalEnvelope {
  account: string;
  envelope: {
    source: string;
    sourceUuid: string;
    sourceName?: string;
    timestamp: number;
    dataMessage?: {
      message: string;
      groupInfo?: {
        groupId: string;
        type: string;
      };
      timestamp: number;
    };
    syncMessage?: {
      sentMessage?: {
        message: string;
        groupInfo?: { groupId: string };
        timestamp: number;
        destination?: string;
      };
    };
  };
}

/** Parsed message ready for processing */
export interface ParsedMessage {
  text: string;
  sender: string;
  senderUuid: string;
  groupId: string;
  timestamp: number;
}

/** A single chat message stored in history (all messages, not just triggered) */
export interface ChatMessage {
  sender: string;
  text: string;
  timestamp: number;
  /** Whether this message was a trigger (had @lattice / /lat prefix) */
  isTriggered: boolean;
}

/** Chat history for a group, passed to the workflow */
export interface ChatHistory {
  /** The triggered message (prefix already stripped) */
  triggered: ParsedMessage;
  /** Recent messages in the group, oldest first (includes non-triggered) */
  recentMessages: ChatMessage[];
}
