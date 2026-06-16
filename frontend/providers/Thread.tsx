import { listThreads, ThreadListItem } from "@/lib/api";
import {
  createContext,
  useContext,
  ReactNode,
  useCallback,
  useState,
  Dispatch,
  SetStateAction,
} from "react";

interface ThreadContextType {
  getThreads: () => Promise<ThreadListItem[]>;
  threads: ThreadListItem[];
  setThreads: Dispatch<SetStateAction<ThreadListItem[]>>;
  threadsLoading: boolean;
  setThreadsLoading: Dispatch<SetStateAction<boolean>>;
}

const ThreadContext = createContext<ThreadContextType | undefined>(undefined);

export function ThreadProvider({ children }: { children: ReactNode }) {
  const [threads, setThreads] = useState<ThreadListItem[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(false);

  const getThreads = useCallback(async (): Promise<ThreadListItem[]> => {
    try {
      setThreadsLoading(true);
      const threads = await listThreads();
      setThreads(threads);
      return threads;
    } catch (error) {
      console.error("Failed to fetch threads:", error);
      setThreads([]);
      return [];
    } finally {
      setThreadsLoading(false);
    }
  }, []);

  const value = {
    getThreads,
    threads,
    setThreads,
    threadsLoading,
    setThreadsLoading,
  };

  return (
    <ThreadContext.Provider value={value}>{children}</ThreadContext.Provider>
  );
}

export function useThreads() {
  const context = useContext(ThreadContext);
  if (context === undefined) {
    throw new Error("useThreads must be used within a ThreadProvider");
  }
  return context;
}
