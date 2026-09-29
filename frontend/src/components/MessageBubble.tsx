import React, { useState, useEffect } from 'react';
import { User, ChevronDown, ChevronUp, Sparkles, Brain, Info } from 'lucide-react';
import type { Message, EvidenceItem } from '../api/client';
import { EvidenceCard } from './EvidenceCard';
import { MarkdownContent } from './MarkdownContent';

interface MessageBubbleProps {
  message: Message;
  isThinking?: boolean;
  onOpenLightbox?: (ev: EvidenceItem) => void;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  isThinking = false,
  onOpenLightbox,
}) => {
  const isUser = message.role === 'user';
  const meta = message.metadata || {};
  const evidenceData = meta.evidence || {};
  const sourceEvidence = evidenceData.source_evidence || [];
  const updateRelation = meta.update_relation || evidenceData.understanding || {};
  const learningState = evidenceData.learning_state || null;
  const learningEvidence = evidenceData.learning_evidence || {};

  const mergedEvidence = React.useMemo(() => {
    const all = [
      ...(Array.isArray(meta.attachments) ? meta.attachments : []),
      ...(Array.isArray(sourceEvidence) ? sourceEvidence : []),
    ];
    const seen = new Map<string, any>();
    for (const item of all) {
      if (!item) continue;
      const key = item.evidence_id
        ? `evidence:${item.evidence_id}`
        : item.canonical_memory_id != null
          ? `memory:${item.canonical_memory_id}`
          : `text:${String(item.text || item.semantic_description || item.original_filename || '').trim()}`;
      const existing = seen.get(key);
      if (!existing) {
        seen.set(key, { ...item });
      } else {
        seen.set(key, { ...existing, ...item, evidence_id: existing.evidence_id || item.evidence_id });
      }
    }
    return Array.from(seen.values());
  }, [meta.attachments, sourceEvidence]);
  const memoryAwareness = meta.memory_awareness || {};
  const isMemoryDisabled = meta.memory_enabled === false;

  const [expandedUnderstanding, setExpandedUnderstanding] = useState(false);
  const [expandedTechnical, setExpandedTechnical] = useState(false);

  // Typing animation effect for newly rendered assistant messages
  const [displayedContent, setDisplayedContent] = useState(
    isUser || !message.content ? message.content : ''
  );

  useEffect(() => {
    if (isUser) {
      setDisplayedContent(message.content);
      return;
    }

    if (!message.content) {
      setDisplayedContent('');
      return;
    }

    if (message.content.length > 500) {
      setDisplayedContent(message.content);
      return;
    }

    let i = 0;
    const speed = Math.max(8, Math.min(25, 1000 / message.content.length));
    const timer = setInterval(() => {
      i += 3;
      setDisplayedContent(message.content.slice(0, i));
      if (i >= message.content.length) {
        clearInterval(timer);
        setDisplayedContent(message.content);
      }
    }, speed);

    return () => clearInterval(timer);
  }, [message.content, isUser]);

  return (
    <div
      style={{
        display: 'flex',
        gap: '14px',
        padding: '16px 20px',
        maxWidth: '860px',
        margin: '0 auto',
        width: '100%',
        alignItems: 'flex-start',
      }}
    >
      {/* Avatar */}
      <div
        style={{
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          background: isUser
            ? 'linear-gradient(135deg, #74806a, #56634c)'
            : 'linear-gradient(135deg, var(--accent-primary), var(--accent-light))',
          color: '#ffffff',
          boxShadow: isUser ? 'none' : '0 3px 10px rgba(77, 99, 59, 0.3)',
        }}
      >
        {isUser ? <User size={18} /> : <Brain size={18} />}
      </div>

      {/* Message Content Container */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '6px',
          }}
        >
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            {isUser ? 'You' : 'Project Memory Agent'}
          </span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            {new Date(message.created_at || Date.now()).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
          {isMemoryDisabled && !isUser && (
            <span
              style={{
                fontSize: '11px',
                color: 'var(--text-muted)',
                backgroundColor: 'var(--bg-card-subtle)',
                padding: '1px 6px',
                borderRadius: '4px',
                border: '1px solid var(--border-subtle)',
              }}
            >
              Memory OFF
            </span>
          )}
        </div>

        {/* Thinking Indicator */}
        {isThinking ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '12px 16px',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '12px',
              width: 'fit-content',
              boxShadow: '0 2px 6px rgba(0,0,0,0.03)',
            }}
          >
            <span
              className="dot-1"
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: 'var(--accent-primary)',
                display: 'inline-block',
              }}
            />
            <span
              className="dot-2"
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: 'var(--accent-light)',
                display: 'inline-block',
              }}
            />
            <span
              className="dot-3"
              style={{
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: '#8da67b',
                display: 'inline-block',
              }}
            />
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', marginLeft: '6px', fontWeight: 500 }}>
              Thinking...
            </span>
          </div>
        ) : (
          /* Main Bubble Content */
          <div
            style={{
              fontSize: '14.5px',
              lineHeight: 1.65,
              color: 'var(--text-primary)',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            <MarkdownContent content={displayedContent} />
          </div>
        )}

        {/* EVIDENCE SECTION (Assistant message only) */}
        {!isUser && !isThinking && (
          <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* 1. Evidence Used */}
            {(sourceEvidence.length > 0 || (meta.attachments && meta.attachments.length > 0)) && (
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '12px',
                  padding: '14px 16px',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.02)',
                }}
              >
                <div
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                    color: 'var(--text-muted)',
                    marginBottom: '10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                >
                  <Sparkles size={14} color="var(--accent-primary)" /> Evidence Used
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {mergedEvidence.map((ev: any, idx: number) => (
                    <EvidenceCard key={`evidence-${ev.evidence_id || ev.canonical_memory_id || idx}`} evidence={ev} onOpenLightbox={onOpenLightbox} />
                  ))}
                </div>
              </div>
            )}

            {/* 2. How This Was Understood (Expandable) */}
            {(updateRelation.understanding || updateRelation.relation || memoryAwareness.reason) && (
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '12px',
                  overflow: 'hidden',
                }}
              >
                <button
                  onClick={() => setExpandedUnderstanding(!expandedUnderstanding)}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 16px',
                    background: 'transparent',
                    color: 'var(--text-secondary)',
                    fontSize: '13px',
                    fontWeight: 500,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Info size={15} color="var(--accent-primary)" />
                    <span>How this was understood</span>
                    {updateRelation.relation && (
                      <span
                        style={{
                          fontSize: '11px',
                          backgroundColor: 'var(--accent-subtle)',
                          color: 'var(--accent-primary)',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontWeight: 600,
                          border: '1px solid rgba(77, 99, 59, 0.2)',
                        }}
                      >
                        {updateRelation.relation}
                      </span>
                    )}
                  </div>
                  {expandedUnderstanding ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>

                {expandedUnderstanding && (
                  <div
                    style={{
                      padding: '14px 16px',
                      borderTop: '1px solid var(--border-subtle)',
                      fontSize: '13px',
                      lineHeight: 1.6,
                      color: 'var(--text-primary)',
                      backgroundColor: 'rgba(234, 228, 213, 0.3)',
                    }}
                  >
                    {updateRelation.understanding && (
                      <div style={{ marginBottom: '8px' }}>
                        <div style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>
                          INTERPRETATION
                        </div>
                        <div>{updateRelation.understanding}</div>
                      </div>
                    )}

                    {updateRelation.missing_information && updateRelation.missing_information !== 'None recorded.' && (
                      <div style={{ marginTop: '8px', color: 'var(--text-secondary)' }}>
                        <div style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>
                          MISSING / UNKNOWN
                        </div>
                        <div>{updateRelation.missing_information}</div>
                      </div>
                    )}

                    {memoryAwareness.reason && (
                      <div style={{ marginTop: '8px' }}>
                        <div style={{ color: 'var(--text-muted)', fontSize: '11px', fontWeight: 600 }}>
                          MEMORY PROBE
                        </div>
                        <div>{memoryAwareness.reason}</div>
                      </div>
                    )}

                    {/* Technical Details Toggle */}
                    <div style={{ marginTop: '12px' }}>
                      <button
                        onClick={() => setExpandedTechnical(!expandedTechnical)}
                        style={{
                          background: 'transparent',
                          color: 'var(--accent-primary)',
                          fontSize: '11px',
                          fontWeight: 600,
                          textDecoration: 'underline',
                          padding: 0,
                        }}
                      >
                        {expandedTechnical ? 'Hide technical details' : 'Show technical details'}
                      </button>

                      {expandedTechnical && (
                        <pre
                          style={{
                            marginTop: '8px',
                            padding: '10px',
                            backgroundColor: 'var(--bg-secondary)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontFamily: 'var(--font-mono)',
                            color: 'var(--text-secondary)',
                            overflowX: 'auto',
                          }}
                        >
                          {JSON.stringify(
                            {
                              canonical_memory_id: message.canonical_memory_id,
                              message_type: message.message_type,
                              evidence_metrics: evidenceData.metrics,
                              relation: updateRelation.relation,
                            },
                            null,
                            2
                          )}
                        </pre>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* 3. Learning / Experience */}
            {(learningState || Object.keys(learningEvidence).length > 0) && (
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '12px',
                  padding: '14px 16px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '7px', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '10px' }}>
                  <Brain size={14} color="var(--accent-primary)" /> Learning / Experience
                </div>
                {learningState ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '8px' }}>
                    <div><span style={{ color: 'var(--text-muted)' }}>Outcomes</span><strong style={{ float: 'right' }}>{learningState.total_outcomes ?? 0}</strong></div>
                    <div><span style={{ color: 'var(--text-muted)' }}>Successes</span><strong style={{ float: 'right' }}>{learningState.successes ?? 0}</strong></div>
                    <div><span style={{ color: 'var(--text-muted)' }}>Failures</span><strong style={{ float: 'right' }}>{learningState.failures ?? 0}</strong></div>
                    <div><span style={{ color: 'var(--text-muted)' }}>Signal</span><strong style={{ float: 'right' }}>{Number(learningState.learning_signal ?? 0).toFixed(2)}</strong></div>
                  </div>
                ) : (
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>No outcome/learning evidence has been recorded for the selected memory yet.</div>
                )}
                {learningEvidence && learningEvidence.memory_id != null && (
                  <div style={{ marginTop: '9px', fontSize: '11.5px', color: 'var(--text-secondary)' }}>
                    Learning is tracked separately from the source memory; recorded feedback is shown here when available.
                  </div>
                )}
              </div>
            )}

            {/* 4. Metrics Bar */}
            {isMemoryDisabled ? (
              <div
                style={{
                  fontSize: '12px',
                  color: 'var(--text-muted)',
                  fontStyle: 'italic',
                  padding: '4px 0',
                }}
              >
                Memory disabled for this response
              </div>
            ) : (
              evidenceData.metrics &&
              Object.keys(evidenceData.metrics).length > 0 && (
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '14px',
                    alignItems: 'center',
                    padding: '8px 0',
                  }}
                >
                  {evidenceData.metrics.retrieval_similarity !== undefined && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Retrieval</span>
                      <div
                        style={{
                          width: '60px',
                          height: '6px',
                          backgroundColor: 'var(--border-subtle)',
                          borderRadius: '3px',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${Math.min(100, Math.round(evidenceData.metrics.retrieval_similarity * 100))}%`,
                            height: '100%',
                            backgroundColor: 'var(--accent-primary)',
                          }}
                        />
                      </div>
                      <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>
                        {Math.round(evidenceData.metrics.retrieval_similarity * 100)}%
                      </span>
                    </div>
                  )}

                  {evidenceData.metrics.query_relevance !== undefined && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Relevance</span>
                      <div
                        style={{
                          width: '60px',
                          height: '6px',
                          backgroundColor: 'var(--border-subtle)',
                          borderRadius: '3px',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${Math.min(100, Math.round(evidenceData.metrics.query_relevance * 100))}%`,
                            height: '100%',
                            backgroundColor: 'var(--accent-light)',
                          }}
                        />
                      </div>
                      <span style={{ color: 'var(--accent-light)', fontWeight: 600 }}>
                        {Math.round(evidenceData.metrics.query_relevance * 100)}%
                      </span>
                    </div>
                  )}

                  {evidenceData.metrics.learning_signal !== undefined && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Signal</span>
                      <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>
                        {Number(evidenceData.metrics.learning_signal).toFixed(2)}
                      </span>
                    </div>
                  )}
                </div>
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
};
