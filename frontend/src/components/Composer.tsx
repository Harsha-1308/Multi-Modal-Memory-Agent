import React, { useState, useRef } from 'react';
import { Paperclip, ArrowUp, X, FileText } from 'lucide-react';

interface AttachedFile {
  file: File;
  previewUrl?: string;
  description: string;
}

interface ComposerProps {
  onSendMessage: (
    content: string,
    files: File[],
    descriptions: { index: number; description: string }[]
  ) => void;
  disabled?: boolean;
}

export const Composer: React.FC<ComposerProps> = ({ onSendMessage, disabled = false }) => {
  const [content, setContent] = useState('');
  const [attachments, setAttachments] = useState<AttachedFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const newFiles: AttachedFile[] = [];

    Array.from(e.target.files).forEach((file) => {
      const isImg = file.type.startsWith('image/');
      newFiles.push({
        file,
        previewUrl: isImg ? URL.createObjectURL(file) : undefined,
        description: '',
      });
    });

    setAttachments([...attachments, ...newFiles]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRemoveAttachment = (index: number) => {
    const target = attachments[index];
    if (target?.previewUrl) {
      URL.revokeObjectURL(target.previewUrl);
    }
    setAttachments(attachments.filter((_, i) => i !== index));
  };

  const handleUpdateDescription = (index: number, desc: string) => {
    const copy = [...attachments];
    copy[index].description = desc;
    setAttachments(copy);
  };

  const handleSend = () => {
    if ((!content.trim() && attachments.length === 0) || disabled) return;

    const files = attachments.map((a) => a.file);
    const descriptions = attachments
      .map((a, idx) => ({ index: idx, description: a.description.trim() }))
      .filter((d) => d.description.length > 0);

    onSendMessage(content.trim(), files, descriptions);

    attachments.forEach((a) => {
      if (a.previewUrl) URL.revokeObjectURL(a.previewUrl);
    });
    setAttachments([]);
    setContent('');

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 180)}px`;
  };

  return (
    <div
      style={{
        maxWidth: '860px',
        margin: '0 auto',
        width: '100%',
        padding: '0 20px 24px 20px',
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '16px',
          padding: '12px 14px',
          boxShadow: '0 6px 20px rgba(0, 0, 0, 0.05)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        {/* Attachment Previews */}
        {attachments.length > 0 && (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '10px',
              padding: '4px',
              borderBottom: '1px solid var(--border-subtle)',
              paddingBottom: '10px',
            }}
          >
            {attachments.map((att, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  backgroundColor: 'var(--bg-card-subtle)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '10px',
                  padding: '6px 10px',
                  maxWidth: '340px',
                }}
              >
                {att.previewUrl ? (
                  <img
                    src={att.previewUrl}
                    alt={att.file.name}
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '6px',
                      objectFit: 'cover',
                    }}
                  />
                ) : (
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '6px',
                      backgroundColor: 'var(--accent-subtle)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--accent-primary)',
                    }}
                  >
                    <FileText size={18} />
                  </div>
                )}

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {att.file.name}
                  </div>
                  <input
                    type="text"
                    placeholder="Statement/description (optional)..."
                    value={att.description}
                    onChange={(e) => handleUpdateDescription(idx, e.target.value)}
                    style={{
                      width: '100%',
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      fontSize: '11px',
                      padding: 0,
                      marginTop: '2px',
                    }}
                  />
                </div>

                <button
                  type="button"
                  onClick={() => handleRemoveAttachment(idx)}
                  style={{
                    background: 'transparent',
                    color: 'var(--text-muted)',
                    padding: '4px',
                    borderRadius: '4px',
                  }}
                  title="Remove attachment"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Input Bar */}
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '10px' }}>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            multiple
            style={{ display: 'none' }}
          />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled}
            style={{
              background: 'transparent',
              color: 'var(--accent-primary)',
              padding: '10px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="Attach image, code, or document"
          >
            <Paperclip size={19} />
          </button>

          <textarea
            ref={textareaRef}
            placeholder="Ask a project question, report a problem, or share an update..."
            value={content}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            rows={1}
            style={{
              flex: 1,
              backgroundColor: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              fontSize: '14.5px',
              lineHeight: 1.5,
              resize: 'none',
              maxHeight: '180px',
              padding: '10px 0',
            }}
          />

          <button
            type="button"
            onClick={handleSend}
            disabled={disabled || (!content.trim() && attachments.length === 0)}
            style={{
              background:
                content.trim() || attachments.length > 0
                  ? 'var(--accent-primary)'
                  : 'var(--border-subtle)',
              color: content.trim() || attachments.length > 0 ? '#fff' : 'var(--text-muted)',
              padding: '9px',
              borderRadius: '9px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: content.trim() || attachments.length > 0 ? '0 2px 8px rgba(77, 99, 59, 0.3)' : 'none',
            }}
          >
            <ArrowUp size={18} />
          </button>
        </div>
      </div>
      <div
        style={{
          textAlign: 'center',
          fontSize: '11px',
          color: 'var(--text-muted)',
          marginTop: '8px',
        }}
      >
        Press Enter to send, Shift+Enter for new line. Memory respects project isolation.
      </div>
    </div>
  );
};
