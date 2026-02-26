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
