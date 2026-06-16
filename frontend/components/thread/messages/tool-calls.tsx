import { AIMessage, ToolMessage } from "@langchain/langgraph-sdk";
import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ChevronDown, ChevronUp, Wrench, Terminal } from "lucide-react";

function isComplexValue(value: any): boolean {
  return Array.isArray(value) || (typeof value === "object" && value !== null);
}

export function ToolCalls({
  toolCalls,
}: {
  toolCalls: AIMessage["tool_calls"];
}) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="flex flex-col gap-2">
      {toolCalls.map((tc, idx) => {
        const args = tc.args as Record<string, any>;
        const hasArgs = Object.keys(args).length > 0;
        return (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05, duration: 0.2 }}
            className="overflow-hidden rounded-xl border border-border bg-card"
          >
            {/* Tool call header */}
            <div className="flex items-center gap-2 border-b border-border bg-muted/50 px-3 py-2">
              <div className="flex size-5 items-center justify-center rounded-md bg-primary/10">
                <Wrench className="size-3 text-primary" />
              </div>
              <span className="text-xs font-semibold text-foreground">{tc.name}</span>
              {tc.id && (
                <code className="ml-auto rounded-md bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                  {tc.id.slice(0, 12)}
                </code>
              )}
            </div>

            {/* Args table */}
            {hasArgs ? (
              <table className="w-full text-xs">
                <tbody className="divide-y divide-border">
                  {Object.entries(args).map(([key, value], argIdx) => (
                    <tr key={argIdx} className="transition-colors hover:bg-muted/30">
                      <td className="w-32 shrink-0 px-3 py-2 font-medium text-muted-foreground">
                        {key}
                      </td>
                      <td className="px-3 py-2 text-foreground">
                        {isComplexValue(value) ? (
                          <code className="block rounded-lg bg-muted px-2 py-1.5 font-mono text-[11px] break-all text-foreground/80">
                            {JSON.stringify(value, null, 2)}
                          </code>
                        ) : (
                          <span className="text-foreground/80">{String(value)}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="px-3 py-2">
                <code className="text-xs text-muted-foreground">{"{}"}</code>
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
}

export function ToolResult({ message }: { message: ToolMessage }) {
  const [isExpanded, setIsExpanded] = useState(false);

  let parsedContent: any;
  let isJsonContent = false;

  try {
    if (typeof message.content === "string") {
      parsedContent = JSON.parse(message.content);
      isJsonContent = isComplexValue(parsedContent);
    }
  } catch {
    parsedContent = message.content;
  }

  const contentStr = isJsonContent
    ? JSON.stringify(parsedContent, null, 2)
    : String(message.content);
  const contentLines = contentStr.split("\n");
  const shouldTruncate = contentLines.length > 4 || contentStr.length > 500;
  const displayedContent =
    shouldTruncate && !isExpanded
      ? contentStr.length > 500
        ? contentStr.slice(0, 500) + "…"
        : contentLines.slice(0, 4).join("\n") + "\n…"
      : contentStr;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      {/* Result header */}
      <div className="flex items-center gap-2 border-b border-border bg-muted/50 px-3 py-2">
        <div className="flex size-5 items-center justify-center rounded-md bg-chart-2/20">
          <Terminal className="size-3 text-chart-2" />
        </div>
        <div className="flex flex-1 items-center gap-2">
          <span className="text-xs font-semibold text-foreground">
            {message.name ? (
              <>
                Result: <span className="text-muted-foreground">{message.name}</span>
              </>
            ) : (
              "Tool Result"
            )}
          </span>
        </div>
        {message.tool_call_id && (
          <code className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
            {message.tool_call_id.slice(0, 12)}
          </code>
        )}
      </div>

      {/* Content */}
      <motion.div
        className="bg-muted/20"
        initial={false}
        animate={{ height: "auto" }}
        transition={{ duration: 0.25 }}
      >
        <div className="p-3">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={isExpanded ? "expanded" : "collapsed"}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
            >
              {isJsonContent ? (
                <table className="w-full text-xs">
                  <tbody className="divide-y divide-border">
                    {(Array.isArray(parsedContent)
                      ? isExpanded
                        ? parsedContent
                        : parsedContent.slice(0, 5)
                      : Object.entries(parsedContent)
                    ).map((item, argIdx) => {
                      const [key, value] = Array.isArray(parsedContent)
                        ? [argIdx, item]
                        : [item[0], item[1]];
                      return (
                        <tr key={argIdx} className="transition-colors hover:bg-muted/30">
                          <td className="w-32 shrink-0 px-3 py-2 font-medium text-muted-foreground">
                            {key}
                          </td>
                          <td className="px-3 py-2 text-foreground/80">
                            {isComplexValue(value) ? (
                              <code className="block rounded-lg bg-muted px-2 py-1.5 font-mono text-[11px] break-all">
                                {JSON.stringify(value, null, 2)}
                              </code>
                            ) : (
                              String(value)
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              ) : (
                <code className="block whitespace-pre-wrap font-mono text-[11px] text-foreground/80">
                  {displayedContent}
                </code>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {((shouldTruncate && !isJsonContent) ||
          (isJsonContent &&
            Array.isArray(parsedContent) &&
            parsedContent.length > 5)) && (
          <motion.button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex w-full cursor-pointer items-center justify-center gap-1.5 border-t border-border py-2 text-xs text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
            whileHover={{ backgroundColor: "var(--muted)" }}
            whileTap={{ scale: 0.99 }}
          >
            {isExpanded ? (
              <>
                <ChevronUp className="size-3.5" />
                Show less
              </>
            ) : (
              <>
                <ChevronDown className="size-3.5" />
                Show more
              </>
            )}
          </motion.button>
        )}
      </motion.div>
    </div>
  );
}
