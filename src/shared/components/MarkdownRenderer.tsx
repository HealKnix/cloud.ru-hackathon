import { memo, useMemo } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { CopyIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import rehypeKatex from 'rehype-katex';
import { useClipboard } from '../hooks/useClipboard';
import { cn } from '../lib/utils';
import { Button } from '../ui/button';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

const InlineCode = ({ value }: { value: string }) => {
  return (
    <code className="inline whitespace-pre-wrap break-words rounded bg-primary/15 px-[0.3rem] py-[0.2rem] font-mono font-medium">
      {value}
    </code>
  );
};

const escapeHtml = (input: string) =>
  input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const CodeBlock = ({
  language,
  value,
}: {
  language: string;
  value: string;
}) => {
  const { copiedHandle, handleCopy } = useClipboard();

  const handleCopyClick = () => {
    void handleCopy(value);
  };

  return (
    <div className="group relative mt-2">
      <div className="overflow-hidden overflow-x-auto rounded-2xl border border-foreground/10 bg-content text-sm leading-relaxed text-foreground">
        <div className="flex items-center gap-2 bg-background px-4 py-2">
          {language}
        </div>
        <div className="flex overflow-auto">
          <div className="not-sm:text-xs px-4 py-2">
            <code
              dangerouslySetInnerHTML={{
                __html: escapeHtml(value),
              }}
            />
          </div>
        </div>
      </div>
      <Button
        size="sm"
        onClick={handleCopyClick}
        variant="ghost"
        className="absolute right-1 top-1 rounded-xl group-hover:flex"
      >
        {copiedHandle ? (
          <span className="flex items-center gap-2">
            <CopyIcon size={14} />
            Скопировано
          </span>
        ) : (
          <span className="flex items-center gap-2">
            <CopyIcon size={14} />
            Копировать
          </span>
        )}
      </Button>
    </div>
  );
};

const componentMapping = () =>
  ({
    h1: ({ ...props }) => (
      <h1
        {...props}
        className="mt-6 scroll-m-20 text-4xl font-semibold leading-tight text-foreground dark:text-white"
      />
    ),
    h2: ({ ...props }) => (
      <h2
        {...props}
        className="mt-6 scroll-m-20 border-b border-primary-foreground/15 pb-2 text-3xl font-semibold leading-snug text-foreground dark:border-primary/25 dark:text-white"
      />
    ),
    h3: ({ ...props }) => (
      <h3
        {...props}
        className="mt-5 scroll-m-20 text-2xl font-semibold leading-snug text-foreground dark:text-white"
      />
    ),
    h4: ({ ...props }) => (
      <h4
        {...props}
        className="mt-4 scroll-m-20 text-xl font-semibold leading-snug text-foreground dark:text-white"
      />
    ),
    p: ({ ...props }) => (
      <p
        {...props}
        className="text-foreground/85 dark:text-white/85 [&:not(:first-child)]:mt-3"
      />
    ),
    strong: ({ ...props }) => (
      <strong
        {...props}
        className="font-semibold text-foreground dark:text-white"
      />
    ),
    em: ({ ...props }) => (
      <em {...props} className="italic text-foreground/80 dark:text-white/80" />
    ),
    ul: ({ ...props }) => (
      <ul
        {...props}
        className="ml-4 mt-3 list-disc space-y-1 text-foreground/85 dark:text-white/80"
      />
    ),
    ol: ({ ...props }) => (
      <ol
        {...props}
        className="ml-4 mt-3 list-decimal space-y-1 text-foreground/85 dark:text-white/80"
      />
    ),
    li: ({ ...props }) => <li {...props} className="leading-relaxed" />,
    blockquote: ({ ...props }) => (
      <blockquote
        {...props}
        className="border-l-3 mt-4 rounded-r-xl border-primary/40 bg-primary/25 px-4 py-2 italic text-foreground/80 dark:border-primary/60 dark:bg-white/[0.04] dark:text-white/70"
      />
    ),
    a: ({ ...props }) => (
      <Link color="primary" to={props.href ?? ''}>
        {props.children}
      </Link>
    ),
    code: ({ children, className }) => {
      const child = String(children ?? '').replace(/\n$/, '');
      const match = /language-([\w-]+)/.exec(className || '');
      const language = match?.[1] ?? null;

      if (match && language) {
        return <CodeBlock language={language} value={child} />;
      }

      return <InlineCode value={child} />;
    },
    table: ({ ...props }) => (
      <div className="bg-content1/50 mt-4 w-full border-collapse overflow-x-hidden rounded-2xl border border-primary text-sm">
        <div className="overflow-x-auto">
          <table {...props} className="w-full" />
        </div>
      </div>
    ),
    thead: ({ ...props }) => (
      <thead
        {...props}
        className="bg-primary/25 text-foreground dark:bg-white/[0.05] dark:text-white"
      />
    ),
    tbody: ({ ...props }) => (
      <tbody
        {...props}
        className="divide-y divide-primary dark:divide-white/5"
      />
    ),
    tr: ({ ...props }) => (
      <tr
        {...props}
        className="odd:bg-transparent even:bg-primary dark:even:bg-white/[0.03]"
      />
    ),
    th: ({ ...props }) => (
      <th
        {...props}
        className="border-border/60 px-4 py-2 text-left font-medium uppercase tracking-wide text-foreground/80 dark:border-white/10 dark:text-white/75"
      />
    ),
    td: ({ ...props }) => (
      <td
        {...props}
        className="border-border/40 px-4 py-2 align-top text-foreground/80 dark:border-white/10 dark:text-white/70"
      />
    ),
    hr: ({ ...props }) => (
      <hr {...props} className="my-6 border-primary/25 dark:border-white/10" />
    ),
    img: ({ ...props }) => (
      <img
        {...props}
        className="my-4 h-auto max-h-[420px] w-full rounded-xl object-contain"
        loading="lazy"
        alt={props.alt ?? ''}
      />
    ),
  }) as Components;

const MarkdownRenderer = ({ content, className }: MarkdownRendererProps) => {
  const sanitizedContent = useMemo(() => content || '', [content]);

  return (
    <div
      className={cn(
        'markdown-body select-text text-[16px] leading-relaxed',
        className,
      )}
    >
      <ReactMarkdown
        children={sanitizedContent}
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeKatex]}
        components={componentMapping()}
      />
    </div>
  );
};

export default memo(
  MarkdownRenderer,
  (prevProps, nextProps) =>
    prevProps.content === nextProps.content &&
    prevProps.className === nextProps.className,
);
