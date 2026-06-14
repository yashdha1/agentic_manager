import React, {
  createContext,
  useContext,
  ReactNode,
  useState,
  useRef,
  useCallback,
  useEffect,
} from "react";
import { type Message } from "@langchain/langgraph-sdk";
import { useQueryState } from "nuqs";
import { sendChatMessage, createThread, StreamEvent } from "@/lib/api";
import { useThreads } from "./Thread";
import { v4 as uuidv4 } from "uuid";
import { toast } from "sonner";

export type StateType = { messages: Message[]; ui?: never[] };

type StreamContextType = {
  messages: Message[];
  isLoading: boolean;
  error: unknown;
  interrupt: unknown;
  stop: () => void;
  submit: (payload: unknown, options?: unknown) => void;
  values: { messages: Message[]; ui: never[] };
  getMessagesMetadata: (_message: Message) => undefined;
  setBranch: (_branch: string) => void;
};

const StreamContext = createContext<StreamContextType | undefined>(undefined);

function StreamSession({ children }: { children: ReactNode }) {
  const [threadId, setThreadId] = useQueryState("threadId");
  const { getThreads, setThreads } = useThreads();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<unknown>(undefined);
  const [interrupt, setInterrupt] = useState<unknown>(null);
  const abortRef = useRef<AbortController | null>(null);
  // Prevents the threadId-change effect from clearing messages we just added
  const justCreatedRef = useRef(false);

  useEffect(() => {
    if (justCreatedRef.current) {
      justCreatedRef.current = false;
      return;
    }
    abortRef.current?.abort();
    setMessages([]);
    setInterrupt(null);
    setError(undefined);
    setIsLoading(false);
  }, [threadId]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setIsLoading(false);
  }, []);

  const submit = useCallback(
    async (payload: unknown, _options?: unknown) => {
      if (isLoading) return;

      const p = payload as { messages?: Message[] } | undefined;
      let messageText = "";
      let humanMsgId = uuidv4();

      if (p?.messages) {
        const lastHuman = [...p.messages].reverse().find((m) => m.type === "human");
        if (lastHuman) {
          humanMsgId = lastHuman.id ?? humanMsgId;
          const content = lastHuman.content;
          if (typeof content === "string") {
            messageText = content;
          } else if (Array.isArray(content)) {
            messageText = content
              .filter((c: unknown) => (c as { type?: string }).type === "text")
              .map((c: unknown) => (c as { text?: string }).text ?? "")
              .join("");
          }
        }
      }

      if (!messageText.trim()) return;

      setError(undefined);
      setInterrupt(null);
      setIsLoading(true);

      const humanMessage: Message = {
        id: humanMsgId,
        type: "human",
        content: messageText,
      };
      setMessages((prev) => [...prev, humanMessage]);

      let tid = threadId;
      if (!tid) {
        try {
          tid = await createThread();
          justCreatedRef.current = true;
          setThreadId(tid);
        } catch (err) {
          setError(err);
          setIsLoading(false);
          setMessages((prev) => prev.filter((m) => m.id !== humanMsgId));
          toast.error("Failed to create thread");
          return;
        }
      }

      const ctrl = new AbortController();
      abortRef.current = ctrl;
      const assistantId = uuidv4();
      let accumulatedContent = "";

      const onEvent = (event: StreamEvent) => {
        if (ctrl.signal.aborted) return;

        if (event.type === "token") {
          accumulatedContent += event.content;
          const snapshot = accumulatedContent;
          setMessages((prev) => {
            const idx = prev.findIndex((m) => m.id === assistantId);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = { ...next[idx], content: snapshot } as Message;
              return next;
            }
            return [...prev, { id: assistantId, type: "ai", content: snapshot } as Message];
          });
        } else if (event.type === "done") {
          const finalContent = event.final_response || accumulatedContent;
          setMessages((prev) => {
            const idx = prev.findIndex((m) => m.id === assistantId);
            if (idx >= 0) {
              const next = [...prev];
              next[idx] = { ...next[idx], content: finalContent } as Message;
              return next;
            }
            return [...prev, { id: assistantId, type: "ai", content: finalContent } as Message];
          });
          setIsLoading(false);
          setTimeout(() => getThreads().then(setThreads).catch(console.error), 1500);
        } else if (event.type === "interrupt") {
          setInterrupt(event.data);
          setIsLoading(false);
        } else if (event.type === "thread_id") {
          const newId = event.data as string;
          if (newId && newId !== tid) {
            setThreadId(newId);
          }
        }
      };

      try {
        await sendChatMessage(tid, messageText, onEvent);
      } catch (err: unknown) {
        if (!ctrl.signal.aborted) {
          setError(err);
          setIsLoading(false);
          toast.error("Chat error", {
            description: (err as Error)?.message,
          });
        }
      } finally {
        if (!ctrl.signal.aborted) {
          setIsLoading(false);
        }
      }
    },
    [isLoading, threadId, setThreadId, getThreads, setThreads],
  );

  const value: StreamContextType = {
    messages,
    isLoading,
    error,
    interrupt,
    stop,
    submit,
    values: { messages, ui: [] },
    getMessagesMetadata: () => undefined,
    setBranch: () => {},
  };

  return (
    <StreamContext.Provider value={value}>{children}</StreamContext.Provider>
  );
}

export const StreamProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => <StreamSession>{children}</StreamSession>;

export const useStreamContext = (): StreamContextType => {
  const context = useContext(StreamContext);
  if (context === undefined) {
    throw new Error("useStreamContext must be used within a StreamProvider");
  }
  return context;
};

export default StreamContext;
