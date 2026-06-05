export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

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

export async function sendChatMessage(threadId: string, message: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, message }),
  });
  if (!response.ok) throw new Error("Failed to send message");
  const data: { content: string } = await response.json();
  return data.content;
}
