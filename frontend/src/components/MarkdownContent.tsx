import React from 'react';

interface MarkdownContentProps {
  content: string;
}

const isSafeUrl = (value: string) => /^https?:\/\//i.test(value.trim());

function renderInline(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|__[^_]+__|\*[^*\n]+\*|_[^_\n]+_|`[^`\n]+`|\[[^\]]+\]\(([^)]+)\))/g;
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) nodes.push(text.slice(last, match.index));
    const token = match[0];

    if ((token.startsWith('**') && token.endsWith('**')) || (token.startsWith('__') && token.endsWith('__'))) {
      nodes.push(<strong key={`b-${match.index}`}>{token.slice(2, -2)}</strong>);
    } else if ((token.startsWith('*') && token.endsWith('*')) || (token.startsWith('_') && token.endsWith('_'))) {
      nodes.push(<em key={`i-${match.index}`}>{token.slice(1, -1)}</em>);
    } else if (token.startsWith('`')) {
      nodes.push(
        <code
          key={`c-${match.index}`}
          style={{
            padding: '2px 5px',
            borderRadius: '4px',
            background: 'var(--bg-card-subtle)',
            border: '1px solid var(--border-subtle)',
            fontFamily: 'var(--font-mono)',
            fontSize: '0.92em',
          }}
        >
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith('[')) {
      const closeBracket = token.indexOf(']');
      const label = token.slice(1, closeBracket);
      const url = token.slice(closeBracket + 2, -1);
      if (isSafeUrl(url)) {
        nodes.push(
          <a key={`a-${match.index}`} href={url} target="_blank" rel="noreferrer">
            {label}
          </a>,
        );
      } else {
        nodes.push(label);
      }
    }
    last = match.index + token.length;
  }

  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

function renderBlock(block: string, index: number): React.ReactNode {
  const lines = block.split('\n');

  if (lines.length === 1) {
    const heading = lines[0].match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      const Tag = (`h${level}` as React.ElementType);
      return <Tag key={`h-${index}`} style={{ margin: '12px 0 6px', lineHeight: 1.3 }}>{renderInline(heading[2])}</Tag>;
    }
  }

  const unordered = lines.every((line) => /^\s*[-*]\s+/.test(line));
  if (unordered) {
    return (
      <ul key={`ul-${index}`} style={{ margin: '8px 0', paddingLeft: '22px' }}>
        {lines.map((line, i) => <li key={i}>{renderInline(line.replace(/^\s*[-*]\s+/, ''))}</li>)}
      </ul>
    );
  }

  const ordered = lines.every((line) => /^\s*\d+[.)]\s+/.test(line));
  if (ordered) {
    return (
      <ol key={`ol-${index}`} style={{ margin: '8px 0', paddingLeft: '22px' }}>
        {lines.map((line, i) => <li key={i}>{renderInline(line.replace(/^\s*\d+[.)]\s+/, ''))}</li>)}
      </ol>
    );
  }

  return (
    <p key={`p-${index}`} style={{ margin: '0 0 10px' }}>
      {lines.map((line, i) => <React.Fragment key={i}>{i > 0 && <br />}{renderInline(line)}</React.Fragment>)}
    </p>
  );
}

export const MarkdownContent: React.FC<MarkdownContentProps> = ({ content }) => {
  const blocks: React.ReactNode[] = [];
  const pieces = content.replace(/\r\n?/g, '\n').split(/\n\s*\n/);

  pieces.forEach((piece, index) => {
    const trimmed = piece.trim();
    if (!trimmed) return;

    const fence = trimmed.match(/^```([\w+-]*)\n([\s\S]*?)```$/);
    if (fence) {
      blocks.push(
        <pre
          key={`code-${index}`}
          style={{
            margin: '10px 0',
            padding: '12px',
            borderRadius: '8px',
            overflowX: 'auto',
            background: 'var(--bg-card-subtle)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <code style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>{fence[2]}</code>
        </pre>,
      );
      return;
    }

    blocks.push(renderBlock(trimmed, index));
  });

  return <div>{blocks}</div>;
};
