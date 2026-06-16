import { PrismAsyncLight as SyntaxHighlighterPrism } from "react-syntax-highlighter";
import tsx from "react-syntax-highlighter/dist/esm/languages/prism/tsx";
import python from "react-syntax-highlighter/dist/esm/languages/prism/python";
import bash from "react-syntax-highlighter/dist/esm/languages/prism/bash";
import json from "react-syntax-highlighter/dist/esm/languages/prism/json";
import yaml from "react-syntax-highlighter/dist/esm/languages/prism/yaml";
import sql from "react-syntax-highlighter/dist/esm/languages/prism/sql";
import markdown from "react-syntax-highlighter/dist/esm/languages/prism/markdown";
import { coldarkDark } from "react-syntax-highlighter/dist/cjs/styles/prism";
import { FC } from "react";

SyntaxHighlighterPrism.registerLanguage("js", tsx);
SyntaxHighlighterPrism.registerLanguage("jsx", tsx);
SyntaxHighlighterPrism.registerLanguage("ts", tsx);
SyntaxHighlighterPrism.registerLanguage("tsx", tsx);
SyntaxHighlighterPrism.registerLanguage("python", python);
SyntaxHighlighterPrism.registerLanguage("bash", bash);
SyntaxHighlighterPrism.registerLanguage("sh", bash);
SyntaxHighlighterPrism.registerLanguage("shell", bash);
SyntaxHighlighterPrism.registerLanguage("json", json);
SyntaxHighlighterPrism.registerLanguage("yaml", yaml);
SyntaxHighlighterPrism.registerLanguage("yml", yaml);
SyntaxHighlighterPrism.registerLanguage("sql", sql);
SyntaxHighlighterPrism.registerLanguage("md", markdown);

interface SyntaxHighlighterProps {
  children: string;
  language: string;
  className?: string;
}

export const SyntaxHighlighter: FC<SyntaxHighlighterProps> = ({
  children,
  language,
  className,
}) => {
  return (
    <SyntaxHighlighterPrism
      language={language}
      style={coldarkDark}
      customStyle={{
        margin: 0,
        width: "100%",
        background: "transparent",
        padding: "1.5rem 1rem",
      }}
      className={className}
    >
      {children}
    </SyntaxHighlighterPrism>
  );
};
