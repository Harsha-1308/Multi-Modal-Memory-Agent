import React from 'react';
import { X, Download, FileText, Image as ImageIcon, ExternalLink } from 'lucide-react';
import { getEvidenceContentUrl } from '../api/client';
import type { EvidenceItem } from '../api/client';

interface EvidenceLightboxProps {
  evidence: EvidenceItem | null;
  onClose: () => void;
}

export const EvidenceLightbox: React.FC<EvidenceLightboxProps> = ({ evidence, onClose }) => {
  if (!evidence) return null;

  const contentUrl = getEvidenceContentUrl(evidence.evidence_id);
  const isImage = evidence.kind === 'image' || evidence.mime_type.startsWith('image/');

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(31, 37, 27, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
        padding: '24px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '900px',
          maxHeight: '90vh',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '16px',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-secondary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {isImage ? <ImageIcon size={20} color="var(--accent-primary)" /> : <FileText size={20} color="var(--accent-primary)" />}
            <div>
              <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>{evidence.original_filename}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {evidence.mime_type} • {(evidence.size_bytes / 1024).toFixed(1)} KB • SHA256: {evidence.sha256.slice(0, 12)}...
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <a
              href={contentUrl}
              target="_blank"
              rel="noopener noreferrer"
              download={evidence.original_filename}
              style={{
                background: 'var(--accent-subtle)',
                color: 'var(--accent-primary)',
                padding: '8px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                textDecoration: 'none',
                border: '1px solid rgba(77, 99, 59, 0.2)',
              }}
              title="Download original file"
            >
              <Download size={16} />
            </a>
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                color: 'var(--text-secondary)',
                padding: '8px',
                borderRadius: '8px',
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Content Preview */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'var(--bg-primary)',
          }}
        >
          {isImage ? (
            <img
              src={contentUrl}
              alt={evidence.original_filename}
              style={{
                maxWidth: '100%',
                maxHeight: '55vh',
                objectFit: 'contain',
                borderRadius: '8px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
                border: '1px solid var(--border-subtle)',
              }}
            />
          ) : (
            <div style={{ textAlign: 'center', padding: '30px' }}>
              <FileText size={48} color="var(--accent-primary)" style={{ marginBottom: '16px' }} />
              <p style={{ fontSize: '15px', color: 'var(--text-primary)', marginBottom: '8px', fontWeight: 600 }}>
                {evidence.original_filename}
              </p>
              <a
                href={contentUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  color: 'var(--accent-primary)',
                  fontSize: '13px',
                  textDecoration: 'none',
                  marginTop: '12px',
                  fontWeight: 600,
                }}
              >
                Open document content <ExternalLink size={14} />
              </a>
            </div>
          )}
        </div>

        {/* Semantic Understanding Footer */}
        {(evidence.user_description || evidence.semantic_description || evidence.combined_understanding) && (
          <div
            style={{
              padding: '16px 20px',
              borderTop: '1px solid var(--border-subtle)',
              backgroundColor: 'var(--bg-secondary)',
              fontSize: '13px',
              lineHeight: 1.6,
            }}
          >
            {evidence.user_description && (
              <div style={{ marginBottom: '6px' }}>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>User Statement: </span>
                <span style={{ color: 'var(--text-primary)' }}>{evidence.user_description}</span>
              </div>
            )}
            {evidence.semantic_description && (
              <div>
                <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>Analysis Understanding: </span>
                <span style={{ color: 'var(--text-secondary)' }}>{evidence.semantic_description}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
