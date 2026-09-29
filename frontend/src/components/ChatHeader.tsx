import React, { useState } from 'react';
import { PanelLeft, Zap, ZapOff } from 'lucide-react';
import type { Chat, Project } from '../api/client';

interface ChatHeaderProps {
  project?: Project;
  chat?: Chat;
  isSidebarOpen: boolean;
  onToggleSidebar: () => void;
  onToggleMemory: (enabled: boolean) => void;
}

export const ChatHeader: React.FC<ChatHeaderProps> = ({
  project,
  chat,
  isSidebarOpen,
  onToggleSidebar,
  onToggleMemory,
}) => {
  const [updating, setUpdating] = useState(false);
  const memoryEnabled = chat?.memory_enabled ?? true;

  const handleToggle = async () => {
    if (updating || !chat) return;
    setUpdating(true);
    try {
      await onToggleMemory(!memoryEnabled);
    } finally {
      setUpdating(false);
    }
  };

  return (
    <header
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 22px',
        borderBottom: '1px solid var(--border-subtle)',
        backgroundColor: memoryEnabled ? 'var(--bg-secondary)' : 'var(--bg-primary-off)',
        backdropFilter: 'blur(8px)',
        zIndex: 10,
        transition: 'background-color 0.35s ease',
      }}
    >
      {/* Left: Sidebar toggle (when sidebar is closed) + Titles */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {!isSidebarOpen && (
          <button
            onClick={onToggleSidebar}
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--accent-primary)',
              padding: '7px 9px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
              fontWeight: 500,
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            }}
            title="Open project sidebar"
          >
            <PanelLeft size={16} />
            <span>Projects</span>
          </button>
        )}

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '15.5px', fontWeight: 600, color: 'var(--text-primary)' }}>
              {chat?.name || 'Select or create a chat'}
            </span>
          </div>
          {project && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '1px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Project:</span>
              <span style={{ fontSize: '11.5px', color: 'var(--text-secondary)', fontWeight: 600 }}>
                {project.name}
              </span>
              <span
                style={{
                  fontSize: '10px',
                  backgroundColor: 'var(--accent-subtle)',
                  color: 'var(--accent-primary)',
                  padding: '1px 6px',
                  borderRadius: '4px',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  border: '1px solid rgba(77, 99, 59, 0.2)',
                }}
              >
                {project.project_type}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Right: Cylindrical / Capsule Toggle Switch */}
      {chat && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            onClick={handleToggle}
            className={`capsule-toggle ${memoryEnabled ? 'active' : 'inactive'}`}
            title={
              memoryEnabled
                ? 'Hindsight memory and project learning are active. Click to turn OFF.'
                : 'Memory disabled. Responses use only this chat context. Click to turn ON.'
            }
          >
            <div className="capsule-knob" />
          </div>

          <div
            onClick={handleToggle}
            style={{
              cursor: 'pointer',
              userSelect: 'none',
              display: 'flex',
              flexDirection: 'column',
              lineHeight: 1.2,
            }}
          >
            <span
              style={{
                fontSize: '12px',
                fontWeight: 600,
                color: memoryEnabled ? 'var(--accent-primary)' : 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              {memoryEnabled ? (
                <>
                  <Zap size={12} fill="currentColor" /> Memory ON
                </>
              ) : (
                <>
                  <ZapOff size={12} /> Memory OFF
                </>
              )}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
              {memoryEnabled ? 'Bank Connected' : 'General Chat Only'}
            </span>
          </div>
        </div>
      )}
    </header>
  );
};
