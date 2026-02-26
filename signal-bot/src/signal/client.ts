import type { SignalEnvelope } from "./types";

export class SignalClient {
  constructor(
    private apiUrl: string,
    private phoneNumber: string,
  ) {}

  /** Poll for new messages */
  async receive(): Promise<SignalEnvelope[]> {
    const url = `${this.apiUrl}/v1/receive/${encodeURIComponent(this.phoneNumber)}`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error(`Signal receive failed: ${resp.status}`);
    return resp.json();
  }

  /** Send a text message to a group, optionally with image attachments */
  async send(
    groupId: string,
    message: string,
    base64Attachments?: string[],
  ): Promise<void> {
    const url = `${this.apiUrl}/v2/send`;
    const body: Record<string, unknown> = {
      message,
      number: this.phoneNumber,
      recipients: [groupId],
    };
    if (base64Attachments?.length) {
      body.base64_attachments = base64Attachments;
    }
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      const text = await resp.text().catch(() => "");
      throw new Error(`Signal send failed: ${resp.status} ${text}`);
    }
  }
}
