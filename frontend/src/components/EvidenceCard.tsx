import React from 'react';
import { FileText, Code, ExternalLink, Hash } from 'lucide-react';
import { getEvidenceContentUrl } from '../api/client';
import type { EvidenceItem } from '../api/client';

interface EvidenceCardProps {
  evidence?: EvidenceItem | any;
  onOpenLightbox?: (ev: EvidenceItem) => void;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ evidence, onOpenLightbox }) => {
  if (!evidence) return null;

  const isStoredFile = Boolean(evidence.evidence_id);
  const isImage = evidence.kind === 'image' || evidence.mime_type?.startsWith('image/');
  const isCode = evidence.kind === 'code';

  if (isStoredFile) {
    const contentUrl = getEvidenceContentUrl(evidence.evidence_id);

    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          alignItems: 'stretch',
          backgroundColor: 'var(--bg-card-subtle)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '10px',
          padding: '10px 14px',
          cursor: isImage ? 'pointer' : 'default',
          transition: 'all 0.15s ease',
        }}
        onClick={() => {
          if (onOpenLightbox) onOpenLightbox(evidence);
        }}
      >
        {/* Thumbnail or Icon */}
        {isImage ? (
          <div
            style={{
              width: '100%',
              height: '190px',
              borderRadius: '6px',
              overflow: 'hidden',
              backgroundColor: '#000',
              flexShrink: 0,
              boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
            }}
          >
            <img
              src={contentUrl}
              alt={evidence.original_filename}
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          </div>
        ) : (
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '8px',
              backgroundColor: 'var(--accent-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              color: 'var(--accent-primary)',
            }}
          >
            {isCode ? <Code size={20} /> : <FileText size={20} />}
          </div>
        )}

        {/* Text information */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: '13px',
              fontWeight: 600,
              color: 'var(--text-primary)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {evidence.original_filename}
          </div>
          <div
            style={{
              fontSize: '12px',
              color: 'var(--text-secondary)',
              marginTop: '2px',
              lineHeight: 1.4,
            }}
          >
            {evidence.user_description || evidence.semantic_description || 'Attached project evidence'}
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Click image to inspect evidence</span>
          <span style={{ color: 'var(--accent-primary)' }}><ExternalLink size={14} /></span>
        </div>
      </div>
    );
  }

  // Source evidence from Hindsight / project canonical memory
  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card-subtle)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '10px',
        padding: '12px 14px',
        fontSize: '13px',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '6px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '3px',
              backgroundColor: 'var(--accent-subtle)',
              color: 'var(--accent-primary)',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '11px',
              fontWeight: 600,
              border: '1px solid rgba(77, 99, 59, 0.2)',
            }}
          >
            <Hash size={10} /> Memory {evidence.canonical_memory_id}
          </span>
          <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
            {evidence.source_kind === 'user_provided_project_update'
              ? 'user project update'
              : 'seeded project memory'}
          </span>
        </div>

        {evidence.retrieval_similarity !== undefined && evidence.retrieval_similarity !== null && (
          <span
            style={{
              fontSize: '11px',
              color: 'var(--accent-primary)',
              fontWeight: 600,
            }}
          >
            sim: {(evidence.retrieval_similarity * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <div style={{ color: 'var(--text-primary)', lineHeight: 1.5 }}>
        "{evidence.text}"
      </div>
    </div>
  );
};
