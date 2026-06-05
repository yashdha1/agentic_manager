"use client";

import { Button } from "@/components/ui/button";
import {
  createThread,
  getThreadMessages,
  listThreads,
  sendChatMessage,
  type ChatMessage,
} from "@/lib/api";
import React, { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { MessageSquare, Plus, Send, Loader2, Bot, User, Sparkles } from "lucide-react";

/* ── Thread sidebar item ─────────────────────────────────── */
function ThreadItem({
  threadId,
  isActive,
  onClick,
  index,
}: {
  threadId: string;
  isActive: boolean;
  onClick: () => void;
  index: number;
}) {
  return (
    <motion.button
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04, duration: 0.25, ease: "easeOut" }}
      onClick={onClick}
      className={`group flex w-full items-center gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm transition-all duration-200 ${
        isActive
          ? "bg-primary/15 text-primary font-medium ring-1 ring-primary/25"
          : "text-muted-foreground hover:bg-accent hover:text-foreground"
      }`}
    >
      <MessageSquare
        className={`size-3.5 shrink-0 transition-colors ${isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"}`}
      />
      <span className="truncate font-mono">{threadId.slice(0, 12)}…</span>
    </motion.button>
  );
}

/* ── Message bubble ──────────────────────────────────────── */
function MessageBubble({
  message,
  index,
}: {
  message: ChatMessage;
  index: number;
}) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        delay: index * 0.03,
        duration: 0.3,
        ease: [0.23, 1, 0.32, 1],
      }}
      className={`flex items-start gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      {/* Avatar */}
      <div
        className={`mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
          isUser
            ? "bg-primary text-primary-foreground shadow-sm"
            : "bg-muted text-muted-foreground ring-1 ring-border"
        }`}
      >
        {isUser ? <User className="size-3.5" /> : <Bot className="size-3.5" />}
      </div>

      {/* Content */}
      <div
        className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm ${
          isUser
            ? "rounded-tr-sm bg-primary text-primary-foreground"
            : "rounded-tl-sm bg-card text-card-foreground ring-1 ring-border"
        }`}
      >
        {message.content}
      </div>
    </motion.div>
  );
}

/* ── Loading indicator ───────────────────────────────────── */
function TypingIndicator() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
      className="flex items-start gap-3"
    >
      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-muted ring-1 ring-border">
        <Bot className="size-3.5 text-muted-foreground" />
      </div>
      <div className="rounded-2xl rounded-tl-sm bg-card px-4 py-3 ring-1 ring-border">
        <div className="flex gap-1.5">
          {[0, 0.2, 0.4].map((delay, i) => (
            <motion.div
              key={i}
              className="size-1.5 rounded-full bg-muted-foreground"
              animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1, 0.8] }}
              transition={{ repeat: Infinity, duration: 1.2, delay, ease: "easeInOut" }}
            />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

/* ── Empty state ─────────────────────────────────────────── */
function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="flex flex-col items-center justify-center gap-4 py-20 text-center"
    >
      <div className="relative flex size-14 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20">
        <Sparkles className="size-6 text-primary" />
        <motion.div
          className="absolute inset-0 rounded-2xl ring-1 ring-primary/30"
          animate={{ scale: [1, 1.15, 1], opacity: [0.5, 0, 0.5] }}
          transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
        />
      </div>
      <div>
        <p className="text-base font-semibold text-foreground">Start a conversation</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Send a message to get started
        </p>
      </div>
    </motion.div>
  );
}

/* ── Main page ───────────────────────────────────────────── */
export default function DemoPage(): React.ReactNode {
  const [mounted, setMounted] = React.useState(false);
  const [threads, setThreads] = React.useState<string[]>([]);
  const [activeThreadId, setActiveThreadId] = React.useState<string | null>(null);
  const [messages, setMessages] = React.useState<ChatMessage[]>([]);
  const [input, setInput] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);
  const [sidebarOpen, setSidebarOpen] = React.useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  React.useEffect(() => setMounted(true), []);

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

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
    textareaRef.current?.focus();
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
        { role: "assistant", content: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [activeThreadId, input, isLoading]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  /* Auto-resize textarea */
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  if (!mounted) return <div className="h-screen w-full bg-background" />;

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Sidebar */}
      <AnimatePresence initial={false}>
        {sidebarOpen && (
          <motion.aside
            key="sidebar"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 260, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 32 }}
            className="flex h-full shrink-0 flex-col overflow-hidden border-r border-border bg-sidebar"
          >
            <div className="flex items-center justify-between p-4 pb-3">
              <div className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-lg bg-primary/15">
                  <Sparkles className="size-3.5 text-primary" />
                </div>
                <span className="text-sm font-semibold text-sidebar-foreground">Agent Chat</span>
              </div>
            </div>

            <div className="px-3 pb-2">
              <Button
                onClick={() => void handleNewChat()}
                variant="secondary"
                size="sm"
                className="w-full justify-start gap-2 rounded-xl font-medium transition-all duration-200 hover:ring-1 hover:ring-border"
              >
                <Plus className="size-3.5" />
                New chat
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto px-2 py-1">
              <AnimatePresence>
                {threads.map((threadId, index) => (
                  <div key={threadId} className="mb-0.5">
                    <ThreadItem
                      threadId={threadId}
                      isActive={activeThreadId === threadId}
                      onClick={() => void loadThread(threadId)}
                      index={index}
                    />
                  </div>
                ))}
              </AnimatePresence>
              {threads.length === 0 && (
                <p className="px-3 py-4 text-xs text-muted-foreground">No threads yet</p>
              )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* Main chat area */}
      <main className="flex min-h-0 flex-1 flex-col">
        {/* Header */}
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          <button
            onClick={() => setSidebarOpen((o) => !o)}
            className="flex size-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
          >
            <MessageSquare className="size-4" />
          </button>
          <span className="text-sm font-medium text-foreground">
            {activeThreadId ? `Thread ${activeThreadId.slice(0, 8)}…` : "New Chat"}
          </span>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto max-w-2xl space-y-4">
            {messages.length === 0 && !isLoading && <EmptyState />}
            {messages.map((message, index) => (
              <MessageBubble key={`${message.role}-${index}`} message={message} index={index} />
            ))}
            <AnimatePresence>{isLoading && <TypingIndicator />}</AnimatePresence>
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <div className="border-t border-border px-4 py-4">
          <div className="mx-auto max-w-2xl">
            <div className="gradient-border relative rounded-2xl bg-muted ring-1 ring-border transition-all duration-200 focus-within:ring-primary/50">
              <div className="flex items-end gap-2 p-2 pl-4">
                <textarea
                  ref={textareaRef}
                  rows={1}
                  value={input}
                  onChange={handleInput}
                  onKeyDown={handleKeyDown}
                  placeholder="Message Agent Chat…"
                  disabled={isLoading}
                  className="max-h-40 min-h-[36px] flex-1 resize-none bg-transparent py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
                  style={{ height: "36px" }}
                />
                <motion.button
                  onClick={() => void handleSend()}
                  disabled={isLoading || !input.trim()}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.93 }}
                  transition={{ type: "spring", stiffness: 400, damping: 20 }}
                  className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm transition-all disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {isLoading ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <Send className="size-4" />
                  )}
                </motion.button>
              </div>
            </div>
            <p className="mt-2 text-center text-xs text-muted-foreground">
              Press Enter to send · Shift+Enter for new line
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
