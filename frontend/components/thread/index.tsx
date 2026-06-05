import { v4 as uuidv4 } from "uuid";
import { ReactNode, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "motion/react";
import { cn } from "@/lib/utils";
import { useStreamContext } from "@/providers/Stream";
import { useState, FormEvent } from "react";
import { Button } from "../ui/button";
import { Checkpoint, Message } from "@langchain/langgraph-sdk";
import { AssistantMessage, AssistantMessageLoading } from "./messages/ai";
import { HumanMessage } from "./messages/human";
import {
  DO_NOT_RENDER_ID_PREFIX,
  ensureToolCallsHaveResponses,
} from "@/lib/ensure-tool-responses";
import { LangGraphLogoSVG } from "../icons/langgraph";
import { TooltipIconButton } from "./tooltip-icon-button";
import {
  ArrowDown,
  LoaderCircle,
  PanelLeftClose,
  PanelLeftOpen,
  SquarePen,
  XIcon,
  Plus,
  Sparkles,
} from "lucide-react";
import { useQueryState, parseAsBoolean } from "nuqs";
import { StickToBottom, useStickToBottomContext } from "use-stick-to-bottom";
import ThreadHistory from "./history";
import { toast } from "sonner";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { Label } from "../ui/label";
import { Switch } from "../ui/switch";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../ui/tooltip";
import { useFileUpload } from "@/hooks/use-file-upload";
import { ContentBlocksPreview } from "./ContentBlocksPreview";
import {
  useArtifactOpen,
  ArtifactContent,
  ArtifactTitle,
  useArtifactContext,
} from "./artifact";

function StickyToBottomContent(props: {
  content: ReactNode;
  footer?: ReactNode;
  className?: string;
  contentClassName?: string;
}) {
  const context = useStickToBottomContext();
  return (
    <div
      ref={context.scrollRef}
      style={{ width: "100%", height: "100%" }}
      className={props.className}
    >
      <div ref={context.contentRef} className={props.contentClassName}>
        {props.content}
      </div>
      {props.footer}
    </div>
  );
}

function ScrollToBottom(props: { className?: string }) {
  const { isAtBottom, scrollToBottom } = useStickToBottomContext();
  if (isAtBottom) return null;
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85, y: 8 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.85, y: 8 }}
      transition={{ type: "spring", stiffness: 400, damping: 28 }}
      className={props.className}
    >
      <Button
        variant="outline"
        size="sm"
        className="rounded-full border-border bg-background/90 shadow-lg backdrop-blur-sm transition-all hover:bg-accent"
        onClick={() => scrollToBottom()}
      >
        <ArrowDown className="h-3.5 w-3.5" />
        <span className="text-xs">Scroll to bottom</span>
      </Button>
    </motion.div>
  );
}

export function Thread() {
  const [artifactContext, setArtifactContext] = useArtifactContext();
  const [artifactOpen, closeArtifact] = useArtifactOpen();

  const [threadId, _setThreadId] = useQueryState("threadId");
  const [chatHistoryOpen, setChatHistoryOpen] = useQueryState(
    "chatHistoryOpen",
    parseAsBoolean.withDefault(false),
  );
  const [hideToolCalls, setHideToolCalls] = useQueryState(
    "hideToolCalls",
    parseAsBoolean.withDefault(false),
  );
  const [input, setInput] = useState("");
  const {
    contentBlocks,
    setContentBlocks,
    handleFileUpload,
    dropRef,
    removeBlock,
    resetBlocks: _resetBlocks,
    dragOver,
    handlePaste,
  } = useFileUpload();
  const [firstTokenReceived, setFirstTokenReceived] = useState(false);
  const isLargeScreen = useMediaQuery("(min-width: 1024px)");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const stream = useStreamContext();
  const messages = stream.messages;
  const isLoading = stream.isLoading;

  const lastError = useRef<string | undefined>(undefined);

  const setThreadId = (id: string | null) => {
    _setThreadId(id);
    closeArtifact();
    setArtifactContext({});
  };

  useEffect(() => {
    if (!stream.error) {
      lastError.current = undefined;
      return;
    }
    try {
      const message = (stream.error as any).message;
      if (!message || lastError.current === message) return;
      lastError.current = message;
      toast.error("An error occurred.", {
        description: (
          <p>
            <strong>Error:</strong> <code>{message}</code>
          </p>
        ),
        richColors: true,
        closeButton: true,
      });
    } catch {
      // no-op
    }
  }, [stream.error]);

  const prevMessageLength = useRef(0);
  useEffect(() => {
    if (
      messages.length !== prevMessageLength.current &&
      messages?.length &&
      messages[messages.length - 1].type === "ai"
    ) {
      setFirstTokenReceived(true);
    }
    prevMessageLength.current = messages.length;
  }, [messages]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if ((input.trim().length === 0 && contentBlocks.length === 0) || isLoading)
      return;
    setFirstTokenReceived(false);

    const newHumanMessage: Message = {
      id: uuidv4(),
      type: "human",
      content: [
        ...(input.trim().length > 0 ? [{ type: "text", text: input }] : []),
        ...contentBlocks,
      ] as Message["content"],
    };

    const toolMessages = ensureToolCallsHaveResponses(stream.messages);
    const context =
      Object.keys(artifactContext).length > 0 ? artifactContext : undefined;

    stream.submit(
      { messages: [...toolMessages, newHumanMessage], context },
      {
        streamMode: ["values"],
        streamSubgraphs: true,
        streamResumable: true,
        optimisticValues: (prev) => ({
          ...prev,
          context,
          messages: [
            ...(prev.messages ?? []),
            ...toolMessages,
            newHumanMessage,
          ],
        }),
      },
    );

    setInput("");
    setContentBlocks([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleRegenerate = (
    parentCheckpoint: Checkpoint | null | undefined,
  ) => {
    prevMessageLength.current = prevMessageLength.current - 1;
    setFirstTokenReceived(false);
    stream.submit(undefined, {
      checkpoint: parentCheckpoint,
      streamMode: ["values"],
      streamSubgraphs: true,
      streamResumable: true,
    });
  };

  const chatStarted = !!threadId || !!messages.length;
  const hasNoAIOrToolMessages = !messages.find(
    (m) => m.type === "ai" || m.type === "tool",
  );

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Sidebar overlay — desktop slide-in */}
      <div className="relative hidden lg:flex">
        <motion.div
          className="absolute z-20 h-full overflow-hidden border-r border-sidebar-border bg-sidebar"
          style={{ width: 280 }}
          animate={{ x: chatHistoryOpen ? 0 : -280 }}
          initial={{ x: -280 }}
          transition={{ type: "spring", stiffness: 300, damping: 32 }}
        >
          <div className="relative h-full" style={{ width: 280 }}>
            <ThreadHistory />
          </div>
        </motion.div>
      </div>

      {/* Main grid — splits for artifact panel */}
      <div
        className={cn(
          "grid w-full transition-[grid-template-columns] duration-500 ease-[cubic-bezier(0.23,1,0.32,1)]",
          artifactOpen ? "grid-cols-[3fr_2fr]" : "grid-cols-[1fr_0fr]",
        )}
      >
        {/* Chat column */}
        <motion.div
          className="relative flex min-w-0 flex-1 flex-col overflow-hidden"
          layout={isLargeScreen}
          animate={{
            marginLeft: chatHistoryOpen && isLargeScreen ? 280 : 0,
          }}
          transition={{ type: "spring", stiffness: 300, damping: 32 }}
        >
          {/* Header */}
          <div className="relative z-10 flex items-center justify-between gap-3 border-b border-border bg-background/80 px-3 py-2.5 backdrop-blur-md">
            <div className="flex items-center gap-2">
              {(!chatHistoryOpen || !isLargeScreen) && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground"
                  onClick={() => setChatHistoryOpen((p) => !p)}
                >
                  {chatHistoryOpen ? (
                    <PanelLeftClose className="size-4" />
                  ) : (
                    <PanelLeftOpen className="size-4" />
                  )}
                </Button>
              )}
              <motion.button
                className="flex cursor-pointer items-center gap-2"
                onClick={() => setThreadId(null)}
                animate={{ marginLeft: chatHistoryOpen && isLargeScreen ? 0 : 0 }}
                whileHover={{ opacity: 0.85 }}
                transition={{ duration: 0.15 }}
              >
                <LangGraphLogoSVG width={24} height={24} />
                <span className="text-base font-semibold tracking-tight">
                  Agent Chat
                </span>
              </motion.button>
            </div>

            <div className="flex items-center gap-1">
              <TooltipIconButton
                size="sm"
                className="size-8 rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground"
                tooltip="New thread"
                variant="ghost"
                onClick={() => setThreadId(null)}
              >
                <SquarePen className="size-4" />
              </TooltipIconButton>
            </div>

            {/* Fade gradient below header */}
            <div className="from-background/80 to-background/0 absolute inset-x-0 top-full h-6 bg-gradient-to-b pointer-events-none" />
          </div>

          {/* Welcome screen */}
          <AnimatePresence>
            {!chatStarted && (
              <motion.div
                key="welcome"
                initial={{ opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -24, scale: 0.96 }}
                transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
                className="pointer-events-none absolute inset-0 z-0 flex items-center justify-center"
              >
                <div className="flex flex-col items-center gap-4 text-center">
                  <div className="relative flex size-16 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/20">
                    <Sparkles className="size-7 text-primary" />
                    <motion.div
                      className="absolute inset-0 rounded-2xl ring-1 ring-primary/30"
                      animate={{ scale: [1, 1.18, 1], opacity: [0.5, 0, 0.5] }}
                      transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
                    />
                  </div>
                  <div>
                    <h1 className="text-2xl font-semibold tracking-tight">
                      Agent Chat
                    </h1>
                    <p className="mt-1.5 text-sm text-muted-foreground">
                      Ask anything — your AI agent is ready
                    </p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Messages */}
          <StickToBottom className="relative flex-1 overflow-hidden">
            <StickyToBottomContent
              className={cn(
                "absolute inset-0 overflow-y-scroll px-4 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:bg-border [&::-webkit-scrollbar-track]:bg-transparent",
                !chatStarted && "mt-[30vh] flex flex-col items-stretch",
                chatStarted && "grid grid-rows-[1fr_auto]",
              )}
              contentClassName="pt-8 pb-6 max-w-3xl mx-auto flex flex-col gap-5 w-full"
              content={
                <>
                  {messages
                    .filter((m) => !m.id?.startsWith(DO_NOT_RENDER_ID_PREFIX))
                    .map((message, index) =>
                      message.type === "human" ? (
                        <HumanMessage
                          key={message.id || `${message.type}-${index}`}
                          message={message}
                          isLoading={isLoading}
                        />
                      ) : (
                        <AssistantMessage
                          key={message.id || `${message.type}-${index}`}
                          message={message}
                          isLoading={isLoading}
                          handleRegenerate={handleRegenerate}
                        />
                      ),
                    )}
                  {hasNoAIOrToolMessages && !!stream.interrupt && (
                    <AssistantMessage
                      key="interrupt-msg"
                      message={undefined}
                      isLoading={isLoading}
                      handleRegenerate={handleRegenerate}
                    />
                  )}
                  {isLoading && !firstTokenReceived && <AssistantMessageLoading />}
                </>
              }
              footer={
                <div className="sticky bottom-0 flex flex-col items-center gap-6 bg-background/80 pb-4 pt-2 backdrop-blur-md">
                  <AnimatePresence>
                    <ScrollToBottom className="absolute bottom-full left-1/2 mb-3 -translate-x-1/2" />
                  </AnimatePresence>

                  {/* Input area */}
                  <div
                    ref={dropRef}
                    className={cn(
                      "relative mx-auto w-full max-w-3xl rounded-2xl bg-muted transition-all duration-300",
                      dragOver
                        ? "ring-2 ring-primary ring-offset-1"
                        : "ring-1 ring-border focus-within:ring-primary/60 focus-within:shadow-[0_0_24px_var(--glow-primary)]",
                    )}
                  >
                    <form
                      onSubmit={handleSubmit}
                      className="grid grid-rows-[1fr_auto] gap-0"
                    >
                      <ContentBlocksPreview
                        blocks={contentBlocks}
                        onRemove={removeBlock}
                      />
                      <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(e) => {
                          setInput(e.target.value);
                          e.target.style.height = "auto";
                          e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
                        }}
                        onPaste={handlePaste}
                        onKeyDown={(e) => {
                          if (
                            e.key === "Enter" &&
                            !e.shiftKey &&
                            !e.metaKey &&
                            !e.nativeEvent.isComposing
                          ) {
                            e.preventDefault();
                            const el = e.target as HTMLElement | undefined;
                            const form = el?.closest("form");
                            form?.requestSubmit();
                          }
                        }}
                        placeholder="Ask anything…"
                        rows={1}
                        className="field-sizing-content min-h-[44px] resize-none border-none bg-transparent px-4 py-3 pb-0 text-sm text-foreground placeholder:text-muted-foreground shadow-none ring-0 outline-none focus:ring-0 focus:outline-none"
                        style={{ height: "44px" }}
                      />

                      <div className="flex items-center gap-4 px-3 pb-3 pt-2">
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div className="flex items-center gap-2">
                                <Switch
                                  id="hide-tool-calls"
                                  checked={hideToolCalls ?? false}
                                  onCheckedChange={setHideToolCalls}
                                  className="scale-90"
                                />
                                <Label
                                  htmlFor="hide-tool-calls"
                                  className="cursor-pointer text-xs text-muted-foreground"
                                >
                                  Hide tools
                                </Label>
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>Toggle tool call visibility</TooltipContent>
                          </Tooltip>
                        </TooltipProvider>

                        <Label
                          htmlFor="file-input"
                          className="flex cursor-pointer items-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground"
                        >
                          <Plus className="size-3.5" />
                          Attach
                        </Label>
                        <input
                          id="file-input"
                          type="file"
                          onChange={handleFileUpload}
                          multiple
                          accept="image/jpeg,image/png,image/gif,image/webp,application/pdf"
                          className="hidden"
                        />

                        {stream.isLoading ? (
                          <motion.div
                            key="stop"
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.8 }}
                            className="ml-auto"
                          >
                            <Button
                              onClick={() => stream.stop()}
                              size="sm"
                              variant="secondary"
                              className="rounded-xl gap-1.5"
                            >
                              <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                              Stop
                            </Button>
                          </motion.div>
                        ) : (
                          <motion.div
                            key="send"
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.8 }}
                            className="ml-auto"
                          >
                            <Button
                              type="submit"
                              size="sm"
                              className="rounded-xl"
                              disabled={
                                isLoading ||
                                (!input.trim() && contentBlocks.length === 0)
                              }
                            >
                              Send
                            </Button>
                          </motion.div>
                        )}
                      </div>
                    </form>
                  </div>
                </div>
              }
            />
          </StickToBottom>
        </motion.div>

        {/* Artifact panel */}
        <div className="relative flex flex-col border-l border-border">
          <div className="absolute inset-0 flex min-w-[28vw] flex-col">
            <div className="flex items-center gap-2 border-b border-border bg-card/60 px-4 py-3 backdrop-blur-sm">
              <ArtifactTitle className="flex-1 truncate overflow-hidden text-sm font-medium" />
              <button
                onClick={closeArtifact}
                className="flex size-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
              >
                <XIcon className="size-4" />
              </button>
            </div>
            <ArtifactContent className="relative flex-grow" />
          </div>
        </div>
      </div>
    </div>
  );
}
