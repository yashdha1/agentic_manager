export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  meta?: { agents: string[]; tools: string[] };
};

export type StreamEvent =
  | { type: "token"; content: string; agent: string }
  | { type: "agent_start"; agent: string }
  | { type: "agent_end"; agent: string }
  | { type: "tool_call"; tool: string; agent: string }
  | { type: "done"; final_response: string }
  | { type: "interrupt"; data: unknown }
  | { type: "thread_id"; data: string }
  | { type: "token_usage"; data: { input_tokens: number; output_tokens: number; total_tokens: number } };

const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export async function listThreads(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/api/v1/threads`, { cache: "no-store" });
  if (!response.ok) throw new Error("Failed to list threads");
  const data: Array<{ thread_id: string }> = await response.json();
  return data.map((item) => item.thread_id);
}

export async function createThread(): Promise<string> {
  const response = await fetch(`${API_BASE}/api/v1/threads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) throw new Error("Failed to create thread");
  const data: { thread_id: string } = await response.json();
  return data.thread_id;
}

export async function getThreadMessages(threadId: string): Promise<ChatMessage[]> {
  const response = await fetch(`${API_BASE}/api/v1/threads/${threadId}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Failed to load thread");
  const data: { messages: ChatMessage[] } = await response.json();
  return data.messages;
}

async function _consumeSSE(
  response: Response,
  onEvent: (event: StreamEvent) => void,
): Promise<string> {
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let finalResponse = "";
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const event = JSON.parse(line.slice(6)) as StreamEvent;
        if (event.type === "done") finalResponse = event.final_response;
        onEvent(event);
      } catch {
        // malformed SSE line — skip
      }
    }
  }
  return finalResponse;
}

/** Stream a new chat message via SSE. Fires onEvent for each event. */
export async function sendChatMessage(
  threadId: string,
  message: string,
  onEvent: (event: StreamEvent) => void,
): Promise<string> {
  const response = await fetch(`${API_BASE}/api/v1/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, message }),
  });
  if (!response.ok) throw new Error("Failed to send message");
  return _consumeSSE(response, onEvent);
}

type InterruptDecision =
  | { type: "approve" }
  | { type: "reject" }
  | { type: "edit"; edited_action: { name: string; args: Record<string, unknown> } };

/**
 * Resume a paused HITL thread with the human's decision.
 * Supports approve, reject, and edit (with edited_action args).
 */
export async function resumeThread(
  threadId: string,
  decision: InterruptDecision,
  onEvent: (event: StreamEvent) => void,
): Promise<string> {
  const response = await fetch(`${API_BASE}/api/v1/chat/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, decisions: [decision] }),
  });
  if (!response.ok) throw new Error("Failed to resume thread");
  return _consumeSSE(response, onEvent);
}
