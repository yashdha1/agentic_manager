"use client";

import {
  createThread,
  getThreadMessages,
  listThreads,
  sendChatMessage,
  resumeThread,
  type ChatMessage,
  type StreamEvent,
  type ThreadListItem,
} from "@/lib/api";
import React, { useRef, useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "motion/react";
import {
  MessageSquare,
  Plus,
  Send,
  Bot,
  User,
  Sparkles,
  Brain,
  ChevronDown,
  Wrench,
  ShieldAlert,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { CSSProperties } from "react";
// react-syntax-highlighter ships CSSProperties but types expect an index signature
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const prismStyle = oneDark as any;

/* ── Types ───────────────────────────────────────────────── */
type StreamState = {
  thinking: string;
  agents: string[];
  tools: string[];
};

/* ── Agent / tool colour map ─────────────────────────────── */
const AGENT_COLORS: Record<string, string> = {
  orchestrator: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  sales:        "bg-green-500/15  text-green-400  border-green-500/30",
  customers:    "bg-blue-500/15   text-blue-400   border-blue-500/30",
  inventory:    "bg-orange-500/15 text-orange-400 border-orange-500/30",
  knowledge:    "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  aggregator:   "bg-cyan-500/15   text-cyan-400   border-cyan-500/30",
};
const DEFAULT_AGENT_COLOR = "bg-muted text-muted-foreground border-border";

function AgentBadge({ name }: { name: string }) {
  const cls = AGENT_COLORS[name] ?? DEFAULT_AGENT_COLOR;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${cls}`}>
      <Bot className="size-3" />{name}
    </span>
  );
}

function ToolBadge({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted px-2 py-0.5 text-[11px] font-medium text-muted-foreground">
      <Wrench className="size-3" />{name}
    </span>
  );
}

/* ── Markdown renderer ───────────────────────────────────── */
function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // @ts-expect-error inline prop from react-markdown
        code({ inline, className, children }) {
          const match = /language-(\w+)/.exec(className ?? "");
          return !inline && match ? (
            <SyntaxHighlighter
              style={prismStyle}
              language={match[1]}
              PreTag="div"
              className="!rounded-xl !text-xs !my-2"
            >
              {String(children).replace(/\n$/, "")}
            </SyntaxHighlighter>
          ) : (
            <code className="rounded bg-muted/80 px-1 py-0.5 font-mono text-[12px] text-foreground">
              {children}
            </code>
          );
        },
        p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
        ul: ({ children }) => <ul className="mb-2 ml-4 list-disc space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2 ml-4 list-decimal space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        h1: ({ children }) => <h1 className="mb-2 text-base font-bold">{children}</h1>,
        h2: ({ children }) => <h2 className="mb-1.5 text-sm font-bold">{children}</h2>,
        h3: ({ children }) => <h3 className="mb-1 text-sm font-semibold">{children}</h3>,
        blockquote: ({ children }) => (
          <blockquote className="my-2 border-l-2 border-primary/40 pl-3 italic text-muted-foreground">
            {children}
          </blockquote>
        ),
        table: ({ children }) => (
          <div className="my-2 overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-xs">{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border-b border-border bg-muted px-3 py-1.5 text-left font-semibold">{children}</th>
        ),
        td: ({ children }) => <td className="border-b border-border/50 px-3 py-1.5">{children}</td>,
        a: ({ children, href }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-2 hover:opacity-80">
            {children}
          </a>
        ),
        strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
        hr: () => <hr className="my-3 border-border/50" />,
      }}
    >
      {content}
    </ReactMarkdown>
  );
}

/* ── Thinking bubble (streaming) ─────────────────────────── */
function ThinkingBubble({ state }: { state: StreamState }) {
  const [expanded, setExpanded] = useState(false);
  const hasActivity = state.agents.length > 0 || state.tools.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.25 }}
      className="flex items-start gap-3"
    >
      {/* Avatar */}
      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-muted ring-1 ring-border">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
        >
          <Brain className="size-3.5 text-primary/70" />
        </motion.div>
      </div>

      {/* Thinking card */}
      <div className="max-w-[78%] w-full rounded-2xl rounded-tl-sm border border-border/60 bg-muted/40 overflow-hidden">
        {/* Header */}
        <button
          onClick={() => setExpanded((e) => !e)}
          className="flex w-full items-center justify-between gap-2 px-4 py-2.5 text-left"
        >
          <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
            <motion.span
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
            >
              Thinking
            </motion.span>
            {state.thinking && (
              <span className="text-[10px] text-muted-foreground/50">
                ({state.thinking.length} chars)
              </span>
            )}
          </span>
          <ChevronDown
            className={`size-3.5 text-muted-foreground/60 transition-transform ${expanded ? "rotate-180" : ""}`}
          />
        </button>

        {/* Activity badges */}
        {hasActivity && (
          <div className="flex flex-wrap gap-1.5 px-4 pb-2.5">
            {state.agents.map((a) => <AgentBadge key={a} name={a} />)}
            {state.tools.map((t) => <ToolBadge key={t} name={t} />)}
          </div>
        )}

        {/* Raw stream (expandable) */}
        <AnimatePresence initial={false}>
          {expanded && state.thinking && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden border-t border-border/40"
            >
              <div className="max-h-48 overflow-y-auto px-4 py-2.5 font-mono text-[11px] leading-relaxed text-muted-foreground/60 whitespace-pre-wrap">
                {state.thinking}
                <span className="inline-block w-1.5 h-3 ml-0.5 bg-muted-foreground/40 animate-pulse" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

/* ── Assistant message (final, markdown) ─────────────────── */
function AssistantMessage({ message, index }: { message: ChatMessage; index: number }) {
  const hasMeta = message.meta && (message.meta.agents.length > 0 || message.meta.tools.length > 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.02, duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
      className="flex items-start gap-3"
    >
      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-muted ring-1 ring-border">
        <Bot className="size-3.5 text-muted-foreground" />
      </div>

      <div className="max-w-[78%] space-y-2">
        {/* Markdown bubble */}
        <div className="rounded-2xl rounded-tl-sm bg-card px-4 py-3 text-sm ring-1 ring-border shadow-sm">
          <MarkdownContent content={message.content} />
        </div>

        {/* Agent / tool footer */}
        {hasMeta && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {message.meta!.agents.map((a) => <AgentBadge key={a} name={a} />)}
            {message.meta!.tools.map((t) => <ToolBadge key={t} name={t} />)}
          </div>
        )}
      </div>
    </motion.div>
  );
}

/* ── User message ────────────────────────────────────────── */
function UserMessage({ message, index }: { message: ChatMessage; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.02, duration: 0.3, ease: [0.23, 1, 0.32, 1] }}
      className="flex items-start gap-3 flex-row-reverse"
    >
      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm">
        <User className="size-3.5" />
      </div>
      <div className="max-w-[78%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground shadow-sm">
        {message.content}
      </div>
    </motion.div>
  );
}

/* ── Thread sidebar item ─────────────────────────────────── */
function ThreadItem({
  threadId,
  title,
  isActive,
  onClick,
  index,
}: {
  threadId: string;
  title: string;
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
      <MessageSquare className={`size-3.5 shrink-0 transition-colors ${isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"}`} />
      <span className="truncate">{title || threadId.slice(0, 12) + "…"}</span>
    </motion.button>
  );
}

/* ── HITL interrupt approval card ───────────────────────── */
type HITLActionRequest = { name?: string; args?: Record<string, unknown>; description?: string };
type HITLReviewConfig = { action_name?: string; allowed_decisions?: string[] };
type HITLInterruptData = { action_requests?: HITLActionRequest[]; review_configs?: HITLReviewConfig[] };

type InterruptDecision =
  | { type: "approve" }
  | { type: "reject" }
  | { type: "edit"; edited_action: { name: string; args: Record<string, unknown> } };

function ArgField({
  fieldKey,
  value,
  onChange,
}: {
  fieldKey: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const isLong = value.length > 60 || value.includes("\n");
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[11px] font-mono text-yellow-400/80">{fieldKey}</label>
      {isLong ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={3}
          className="w-full rounded-lg bg-muted/60 px-3 py-2 text-[12px] font-mono text-foreground border border-yellow-500/20 focus:border-yellow-400/50 focus:outline-none resize-y"
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-lg bg-muted/60 px-3 py-2 text-[12px] font-mono text-foreground border border-yellow-500/20 focus:border-yellow-400/50 focus:outline-none"
        />
      )}
    </div>
  );
}

function InterruptCard({
  data,
  onDecision,
  disabled,
}: {
  data: unknown;
  onDecision: (d: InterruptDecision) => void;
  disabled: boolean;
}) {
  const hitl = data as HITLInterruptData;
  const actions = hitl?.action_requests ?? [];
  const first = actions[0] ?? {};
  const toolName = first.name ?? "Action";
  const rawArgs = first.args ?? {};

  // Build editable state — exclude "confirmed" (internal flag), stringify complex values
  const displayEntries = Object.entries(rawArgs).filter(([k]) => k !== "confirmed");
  const initialFields = Object.fromEntries(
    displayEntries.map(([k, v]) => [
      k,
      v === null || v === undefined ? "" : typeof v === "object" ? JSON.stringify(v, null, 2) : String(v),
    ])
  );

  const [fields, setFields] = React.useState<Record<string, string>>(initialFields);

  // Detect missing required fields (null/undefined/empty in original args)
  const missingFields = displayEntries
    .filter(([, v]) => v === null || v === undefined || v === "")
    .map(([k]) => k);

  const hasEdits = displayEntries.some(([k]) => fields[k] !== initialFields[k]);

  const buildEditedArgs = (): Record<string, unknown> => {
    const out: Record<string, unknown> = { ...rawArgs };
    for (const [k, strVal] of Object.entries(fields)) {
      const orig = rawArgs[k];
      if (typeof orig === "number") {
        const n = Number(strVal);
        out[k] = Number.isNaN(n) ? strVal : n;
      } else if (typeof orig === "boolean") {
        out[k] = strVal === "true";
      } else {
        try {
          out[k] = JSON.parse(strVal);
        } catch {
          out[k] = strVal;
        }
      }
    }
    return out;
  };

  const handleApprove = () => {
    if (hasEdits || missingFields.length > 0) {
      onDecision({
        type: "edit",
        edited_action: { name: toolName, args: { ...buildEditedArgs(), confirmed: true } },
      });
    } else {
      onDecision({ type: "approve" });
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.25 }}
      className="mx-auto max-w-2xl"
    >
      <div className="rounded-2xl border border-yellow-500/30 bg-yellow-500/5 overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-2.5 px-4 py-3 border-b border-yellow-500/20">
          <ShieldAlert className="size-4 text-yellow-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-yellow-300">Approval Required</p>
            <p className="text-xs text-yellow-400/70 font-mono truncate">{toolName}</p>
          </div>
          {actions.length > 1 && (
            <span className="text-xs text-yellow-400/60 shrink-0">{actions.length} actions</span>
          )}
        </div>

        {/* Missing field notice */}
        {missingFields.length > 0 && (
          <div className="px-4 pt-3">
            <p className="text-[11px] text-yellow-300/80 bg-yellow-500/10 rounded-lg px-3 py-2 border border-yellow-500/20">
              Required field{missingFields.length > 1 ? "s" : ""} missing:{" "}
              <span className="font-mono font-semibold">{missingFields.join(", ")}</span>
              {" — "}please fill in below before approving.
            </p>
          </div>
        )}

        {/* Editable parameters */}
        <div className="px-4 py-3 space-y-3">
          {displayEntries.map(([k]) => (
            <ArgField
              key={k}
              fieldKey={k}
              value={fields[k] ?? ""}
              onChange={(v) => setFields((prev) => ({ ...prev, [k]: v }))}
            />
          ))}
        </div>

        {/* Actions */}
        <div className="flex gap-2 px-4 pb-4">
          <button
            onClick={handleApprove}
            disabled={disabled || missingFields.some((f) => !fields[f]?.trim())}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-green-500/15 border border-green-500/30 px-4 py-2.5 text-sm font-medium text-green-400 transition-all hover:bg-green-500/25 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <CheckCircle2 className="size-4" />
            {hasEdits || missingFields.length > 0 ? "Edit & Approve" : "Approve"}
          </button>
          <button
            onClick={() => onDecision({ type: "reject" })}
            disabled={disabled}
            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-red-500/15 border border-red-500/30 px-4 py-2.5 text-sm font-medium text-red-400 transition-all hover:bg-red-500/25 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <XCircle className="size-4" />
            Reject
          </button>
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
        <p className="mt-1 text-sm text-muted-foreground">Send a message to get started</p>
      </div>
    </motion.div>
  );
}

/* ── Main page ───────────────────────────────────────────── */
export default function DemoPage(): React.ReactNode {
  const [mounted, setMounted] = useState(false);
  const [threads, setThreads] = useState<ThreadListItem[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamState, setStreamState] = useState<StreamState | null>(null);
  const [interruptData, setInterruptData] = useState<unknown | null>(null);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const streamRef = useRef<StreamState>({ thinking: "", agents: [], tools: [] });

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamState]);

  const loadThread = useCallback(async (threadId: string) => {
    setActiveThreadId(threadId);
    setStreamState(null);
    setInterruptData(null);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "36px";
    try {
      const data = await getThreadMessages(threadId);
      setMessages(data);
    } catch {
      // Thread not found or unreachable — show empty state for this thread
      setMessages([]);
    }
  }, []);

  const handleNewChat = useCallback(async () => {
    const threadId = await createThread();
    const newThread: ThreadListItem = { thread_id: threadId, title: "New Chat", created_at: new Date().toISOString() };
    setThreads((prev) => [newThread, ...prev]);
    setActiveThreadId(threadId);
    setMessages([]);
    setStreamState(null);
    setInterruptData(null);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "36px";
    textareaRef.current?.focus();
  }, []);

  useEffect(() => {
    async function init() {
      try {
        const allThreads = await listThreads();
        setThreads(allThreads);
        if (allThreads.length > 0) await loadThread(allThreads[0].thread_id);
      } catch {
        // Backend unreachable — start with an empty state so the UI still loads
      }
    }
    void init();
  }, [loadThread]);

  const handleSend = useCallback(async () => {
    const message = input.trim();
    if (!message || isLoading) return;

    setIsLoading(true);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "36px";

    let threadId = activeThreadId;
    if (!threadId) {
      threadId = await createThread();
      const newThread: ThreadListItem = { thread_id: threadId as string, title: input.trim().slice(0, 80), created_at: new Date().toISOString() };
      setThreads((prev) => [newThread, ...prev]);
      setActiveThreadId(threadId);
      setMessages([]);
    }

    setMessages((prev) => [...prev, { role: "user", content: message }]);

    // Initialise stream state
    streamRef.current = { thinking: "", agents: [], tools: [] };
    setStreamState({ thinking: "", agents: [], tools: [] });

    let interrupted = false;
    const handleEvent = (event: StreamEvent) => {
      if (event.type === "token") {
        streamRef.current = {
          ...streamRef.current,
          thinking: streamRef.current.thinking + event.content,
        };
        setStreamState({ ...streamRef.current });
      } else if (event.type === "agent_start") {
        if (!streamRef.current.agents.includes(event.agent)) {
          streamRef.current = { ...streamRef.current, agents: [...streamRef.current.agents, event.agent] };
          setStreamState({ ...streamRef.current });
        }
      } else if (event.type === "tool_call") {
        if (!streamRef.current.tools.includes(event.tool)) {
          streamRef.current = { ...streamRef.current, tools: [...streamRef.current.tools, event.tool] };
          setStreamState({ ...streamRef.current });
        }
      } else if (event.type === "interrupt") {
        // Graph paused — surface the interrupt card; keep stream state visible
        interrupted = true;
        setInterruptData(event.data);
        setIsLoading(false);
      }
    };

    try {
      const finalResponse = await sendChatMessage(threadId, message, handleEvent);
      // Only finalise if no interrupt happened (interrupt sets isLoading=false early)
      if (!interrupted) {
        const meta = { agents: streamRef.current.agents, tools: streamRef.current.tools };
        setStreamState(null);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: finalResponse || streamRef.current.thinking, meta },
        ]);
      }
    } catch {
      setStreamState(null);
      setInterruptData(null);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong. Please try again." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [activeThreadId, input, isLoading]);

  const handleDecision = useCallback(async (decision: InterruptDecision) => {
    if (!activeThreadId || isLoading) return;
    setInterruptData(null);
    setIsLoading(true);
    // Keep existing stream state agents/tools; reset thinking text for the new pass
    streamRef.current = { ...streamRef.current, thinking: "" };
    setStreamState({ ...streamRef.current });

    let interrupted = false;
    const handleEvent = (event: StreamEvent) => {
      if (event.type === "token") {
        streamRef.current = { ...streamRef.current, thinking: streamRef.current.thinking + event.content };
        setStreamState({ ...streamRef.current });
      } else if (event.type === "agent_start") {
        if (!streamRef.current.agents.includes(event.agent)) {
          streamRef.current = { ...streamRef.current, agents: [...streamRef.current.agents, event.agent] };
          setStreamState({ ...streamRef.current });
        }
      } else if (event.type === "tool_call") {
        if (!streamRef.current.tools.includes(event.tool)) {
          streamRef.current = { ...streamRef.current, tools: [...streamRef.current.tools, event.tool] };
          setStreamState({ ...streamRef.current });
        }
      } else if (event.type === "interrupt") {
        interrupted = true;
        setInterruptData(event.data);
        setIsLoading(false);
      }
    };

    try {
      const finalResponse = await resumeThread(activeThreadId, decision, handleEvent);
      if (interrupted) return;
      const meta = { agents: streamRef.current.agents, tools: streamRef.current.tools };
      setStreamState(null);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: finalResponse || streamRef.current.thinking, meta },
      ]);
    } catch {
      setStreamState(null);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, something went wrong during resume." },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [activeThreadId, isLoading]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

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
                {threads.map((t, index) => (
                  <div key={t.thread_id} className="mb-0.5">
                    <ThreadItem
                      threadId={t.thread_id}
                      title={t.title}
                      isActive={activeThreadId === t.thread_id}
                      onClick={() => void loadThread(t.thread_id)}
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
            {messages.length === 0 && !streamState && <EmptyState />}

            {messages.map((message, index) =>
              message.role === "user" ? (
                <UserMessage key={`u-${index}`} message={message} index={index} />
              ) : (
                <AssistantMessage key={`a-${index}`} message={message} index={index} />
              )
            )}

            <AnimatePresence>
              {streamState && <ThinkingBubble key="thinking" state={streamState} />}
            </AnimatePresence>

            <AnimatePresence>
              {interruptData != null && (
                <InterruptCard
                  key="interrupt"
                  data={interruptData}
                  onDecision={(d) => void handleDecision(d)}
                  disabled={isLoading}
                />
              )}
            </AnimatePresence>

            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <div className="border-t border-border px-4 py-4">
          <div className="mx-auto max-w-2xl">
            <div className="relative rounded-2xl bg-muted ring-1 ring-border transition-all duration-200 focus-within:ring-primary/50">
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
                  <Send className="size-4" />
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
