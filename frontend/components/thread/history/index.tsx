import { Button } from "@/components/ui/button";
import { useThreads } from "@/providers/Thread";
import { ThreadListItem } from "@/lib/api";
import { useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";

import { useQueryState, parseAsBoolean } from "nuqs";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { PanelLeftClose, SquarePen, MessageSquare } from "lucide-react";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { cn } from "@/lib/utils";

function ThreadItem({
  thread,
  isActive,
  onClick,
  index,
}: {
  thread: ThreadListItem;
  isActive: boolean;
  onClick: () => void;
  index: number;
}) {
  // Use title from backend, fall back to thread_id if title is empty
  const itemText = thread.title || thread.thread_id;

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.03, duration: 0.22, ease: "easeOut" }}
    >
      <button
        onClick={onClick}
        className={cn(
          "group flex w-full items-start gap-2.5 rounded-xl px-3 py-2.5 text-left text-sm transition-all duration-150",
          isActive
            ? "bg-sidebar-accent text-sidebar-foreground font-medium ring-1 ring-sidebar-border"
            : "text-sidebar-foreground/70 hover:bg-sidebar-accent/70 hover:text-sidebar-foreground",
        )}
      >
        <MessageSquare
          className={cn(
            "mt-0.5 size-3.5 shrink-0 transition-colors",
            isActive ? "text-sidebar-primary" : "text-sidebar-foreground/40 group-hover:text-sidebar-foreground/70",
          )}
        />
        <p className="truncate leading-snug">{itemText}</p>
      </button>
    </motion.div>
  );
}

function ThreadHistoryLoading() {
  return (
    <div className="flex flex-col gap-1 px-2">
      {Array.from({ length: 12 }).map((_, i) => (
        <motion.div
          key={`skeleton-${i}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: i * 0.04 }}
        >
          <Skeleton className="h-9 w-full rounded-xl bg-sidebar-accent/50" />
        </motion.div>
      ))}
    </div>
  );
}

function ThreadList({
  threads,
  onThreadClick,
}: {
  threads: ThreadListItem[];
  onThreadClick?: (threadId: string) => void;
}) {
  const [threadId, setThreadId] = useQueryState("threadId");

  return (
    <div className="flex h-full w-full flex-col gap-0.5 overflow-y-auto px-2 pb-4">
      <AnimatePresence>
        {threads.map((t, i) => (
          <ThreadItem
            key={t.thread_id}
            thread={t}
            isActive={t.thread_id === threadId}
            index={i}
            onClick={() => {
              onThreadClick?.(t.thread_id);
              if (t.thread_id === threadId) return;
              setThreadId(t.thread_id);
            }}
          />
        ))}
      </AnimatePresence>
      {threads.length === 0 && (
        <p className="px-3 py-4 text-xs text-sidebar-foreground/40">
          No conversations yet
        </p>
      )}
    </div>
  );
}

export default function ThreadHistory() {
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");
  const [chatHistoryOpen, setChatHistoryOpen] = useQueryState(
    "chatHistoryOpen",
    parseAsBoolean.withDefault(false),
  );
  const [, setThreadId] = useQueryState("threadId");

  const { getThreads, threads, setThreads, threadsLoading, setThreadsLoading } =
    useThreads();

  useEffect(() => {
    if (typeof window === "undefined") return;
    setThreadsLoading(true);
    getThreads()
      .then(setThreads)
      .catch(console.error)
      .finally(() => setThreadsLoading(false));
  }, []);

  const sidebar = (
    <div className="flex h-full w-full flex-col">
      {/* Sidebar header */}
      <div className="flex items-center justify-between px-3 py-3">
        <span className="text-xs font-semibold uppercase tracking-widest text-sidebar-foreground/40">
          Conversations
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="size-7 rounded-lg text-sidebar-foreground/50 hover:bg-sidebar-accent hover:text-sidebar-foreground"
            onClick={() => {
              setThreadId(null);
            }}
          >
            <SquarePen className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="size-7 rounded-lg text-sidebar-foreground/50 hover:bg-sidebar-accent hover:text-sidebar-foreground"
            onClick={() => setChatHistoryOpen((p) => !p)}
          >
            <PanelLeftClose className="size-3.5" />
          </Button>
        </div>
      </div>

      {/* Thread list */}
      <div className="flex-1 overflow-hidden">
        {threadsLoading ? <ThreadHistoryLoading /> : <ThreadList threads={threads} />}
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop sidebar — embedded in motion panel */}
      <div className="hidden h-full w-[280px] shrink-0 lg:flex">
        {sidebar}
      </div>

      {/* Mobile sheet */}
      <div className="lg:hidden">
        <Sheet
          open={!!chatHistoryOpen && !isLargeScreen}
          onOpenChange={(open) => {
            if (isLargeScreen) return;
            setChatHistoryOpen(open);
          }}
        >
          <SheetContent
            side="left"
            className="w-[280px] border-r border-sidebar-border bg-sidebar p-0"
          >
            <SheetHeader className="sr-only">
              <SheetTitle>Conversation History</SheetTitle>
            </SheetHeader>
            <div className="h-full">
              {sidebar}
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
