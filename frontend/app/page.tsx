"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createThread,
  getThreadMessages,
  listThreads,
  sendChatMessage,
  type ChatMessage,
} from "@/lib/api";
import React from "react";

export default function DemoPage(): React.ReactNode {
  const [threads, setThreads] = React.useState<string[]>([]);
  const [activeThreadId, setActiveThreadId] = React.useState<string | null>(null);
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [input, setInput] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);

  const loadThread = React.useCallback(async (threadId: string) => {
    setActiveThreadId(threadId);
    const data = await getThreadMessages(threadId);
    setMessages(data);
  }, []);

  const handleNewChat = React.useCallback(async () => {
    const threadId = await createThread();
    setThreads((prev) => [threadId, ...prev]);
    setActiveThreadId(threadId);
    setMessages([]);
  }, []);

  React.useEffect(() => {
    async function init() {
      const allThreads = await listThreads();
      setThreads(allThreads);
      if (allThreads.length > 0) {
        await loadThread(allThreads[0]);
      }
    }

    void init();
  }, [loadThread]);

  const handleSend = React.useCallback(async () => {
    const message = input.trim();
    if (!message || isLoading) return;

    setIsLoading(true);
    setInput("");

    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createThread();
      setThreads((prev) => [threadId as string, ...prev]);
      setActiveThreadId(threadId);
      setMessages([]);
    }

    setMessages((prev) => [...prev, { role: "user", content: message }]);

    try {
      const assistantReply = await sendChatMessage(threadId, message);
      setMessages((prev) => [...prev, { role: "assistant", content: assistantReply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Unable to fetch response." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [activeThreadId, input, isLoading]);

  return (
    <div className="flex h-screen w-full flex-col bg-[#141414] text-zinc-100 md:flex-row">
      <aside className="w-full border-b border-zinc-800 bg-[#0f0f0f] p-3 md:w-72 md:border-r md:border-b-0">
        <Button className="w-full" variant="secondary" onClick={() => void handleNewChat()}>
          New chat
        </Button>
        <div className="mt-3 flex gap-2 overflow-x-auto md:block md:space-y-2">
          {threads.map((threadId) => (
            <button
              key={threadId}
              onClick={() => void loadThread(threadId)}
              className={`rounded-md border px-3 py-2 text-left text-sm transition md:block md:w-full ${
                activeThreadId === threadId
                  ? "border-zinc-500 bg-zinc-800"
                  : "border-zinc-800 bg-zinc-900 hover:bg-zinc-800"
              }`}
            >
              {threadId.slice(0, 8)}
            </button>
          ))}
        </div>
      </aside>

      <main className="flex min-h-0 flex-1 flex-col bg-[#141414]">
        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.length === 0 && (
              <div className="text-sm text-zinc-400">Start a chat by sending a message.</div>
            )}
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`rounded-xl px-4 py-3 text-sm leading-6 ${
                  message.role === "user"
                    ? "ml-auto max-w-[80%] bg-zinc-700 text-zinc-100"
                    : "max-w-[90%] bg-zinc-900 text-zinc-100"
                }`}
              >
                {message.content}
              </div>
            ))}
          </div>
        </div>

        <div className="border-t border-zinc-800 p-4 md:p-6">
          <div className="mx-auto flex max-w-3xl gap-2">
            <Input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void handleSend();
                }
              }}
              placeholder="Message"
              className="border-zinc-700 bg-zinc-900 text-zinc-100 placeholder:text-zinc-500"
              disabled={isLoading}
            />
            <Button onClick={() => void handleSend()} disabled={isLoading || !input.trim()}>
              Send
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
