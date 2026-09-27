import ReactMarkdown, { type Components } from "react-markdown";

// react-markdown doesn't render raw HTML by default, so model output can't
// inject markup into the page.
const components: Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="mb-2 list-disc space-y-0.5 pl-5 last:mb-0">{children}</ul>,
  ol: ({ children }) => (
    <ol className="mb-2 list-decimal space-y-0.5 pl-5 last:mb-0">{children}</ol>
  ),
  strong: ({ children }) => <strong className="font-semibold text-stone-900">{children}</strong>,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-amber-700 underline">
      {children}
    </a>
  ),
  code: ({ children }) => (
    <code className="rounded bg-stone-100 px-1 font-mono text-[0.85em]">{children}</code>
  ),
};

export default function Markdown({ children }: { children: string }) {
  return <ReactMarkdown components={components}>{children}</ReactMarkdown>;
}
