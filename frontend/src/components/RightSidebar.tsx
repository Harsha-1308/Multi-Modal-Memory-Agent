import React, { useEffect, useState } from 'react';
import { Database, ShieldCheck, Sparkles, BookOpen, RefreshCw } from 'lucide-react';
import type { Project } from '../api/client';
import { getProjectMemories } from '../api/client';

interface RightSidebarProps {
  isOpen: boolean;
  project?: Project;
  memoryEnabled?: boolean;
  onOpenMemoriesModal?: () => void;
  refreshKey?: number;
}

export const RightSidebar: React.FC<RightSidebarProps> = ({
  isOpen,
  project,
  memoryEnabled = true,
  onOpenMemoriesModal,
  refreshKey = 0,
}) => {
  const [memories, setMemories] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    if (!project?.project_id) {
      setMemories([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setMemories(await getProjectMemories(project.project_id));
    } catch (err: any) {
      setError(err?.message || 'Unable to load memory bank.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) refresh();
  }, [isOpen, project?.project_id, refreshKey]);

  return (
    <aside style={{
      width: isOpen ? '310px' : '0px', minWidth: isOpen ? '310px' : '0px', opacity: isOpen ? 1 : 0,
      pointerEvents: isOpen ? 'auto' : 'none', height: '100%', backgroundColor: 'var(--bg-secondary)',
      borderLeft: isOpen ? '1px solid var(--border-subtle)' : 'none', display: 'flex', flexDirection: 'column',
      transition: 'width 0.35s ease, opacity 0.25s ease, min-width 0.35s ease', overflow: 'hidden', zIndex: 20,
    }}>
      <div style={{ width: '310px', display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={{ padding: '16px 18px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: 'rgba(234, 228, 213, 0.7)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: memoryEnabled ? 'var(--accent-primary)' : 'var(--text-muted)' }} />
            <span style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--text-primary)' }}>Memory & Context</span>
          </div>
          <span style={{ fontSize: '11px', backgroundColor: memoryEnabled ? 'var(--accent-subtle)' : 'var(--bg-card-subtle)', color: memoryEnabled ? 'var(--accent-primary)' : 'var(--text-muted)', padding: '2px 8px', borderRadius: '12px', fontWeight: 600, border: '1px solid var(--border-subtle)' }}>
            {memoryEnabled ? 'Memory ON' : 'Memory OFF'}
          </span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '18px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {project && (
            <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '13px 14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '9px' }}>
                <Database size={15} color="var(--accent-primary)" />
                <span style={{ fontSize: '12px', fontWeight: 600 }}>Hindsight Memory Bank</span>
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', wordBreak: 'break-all', lineHeight: 1.45 }}>{project.hindsight_bank_id}</div>
            </div>
          )}

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '13px 14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '9px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
                <ShieldCheck size={15} color="var(--accent-primary)" />
                <span style={{ fontSize: '12px', fontWeight: 600 }}>Verified Project Memory</span>
              </div>
              <button onClick={refresh} disabled={loading} title="Refresh memory" style={{ background: 'transparent', padding: '4px', color: 'var(--text-secondary)' }}><RefreshCw size={14} className={loading ? 'animate-spin' : ''} /></button>
            </div>
            <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--text-primary)' }}>{memories.length}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>{memoryEnabled ? 'Canonical memories available to the project agent.' : 'Retrieval is paused while Memory is OFF.'}</div>
          </div>

          {error && <div style={{ fontSize: '11.5px', color: 'var(--danger)', padding: '10px', borderRadius: '8px', background: 'rgba(185, 28, 28, 0.08)' }}>{error}</div>}

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '8px', fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              <Sparkles size={14} color="var(--accent-primary)" /> Recent memories
            </div>
            {loading && memories.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', padding: '12px' }}>Loading memory context…</div>
            ) : memories.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', padding: '12px', border: '1px dashed var(--border-subtle)', borderRadius: '8px' }}>No verified memories yet.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {memories.slice(-6).reverse().map((m) => (
                  <div key={m.canonical_memory_id} style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: '9px', padding: '10px 11px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', marginBottom: '5px' }}>
                      <span style={{ fontSize: '10.5px', fontWeight: 700, color: 'var(--accent-primary)' }}>Memory {m.canonical_memory_id}</span>
                      {m.learning_state?.total_outcomes > 0 && <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{m.learning_state.total_outcomes} outcomes</span>}
                    </div>
                    <div style={{ fontSize: '12px', lineHeight: 1.45, color: 'var(--text-primary)' }}>{m.text}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {onOpenMemoriesModal && <button onClick={onOpenMemoriesModal} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '7px', width: '100%', padding: '10px 14px', borderRadius: '8px', backgroundColor: 'var(--accent-subtle)', color: 'var(--accent-primary)', fontSize: '12px', fontWeight: 600, border: '1px solid rgba(77, 99, 59, 0.25)' }}><BookOpen size={14} /> Open full memory bank</button>}
        </div>
      </div>
    </aside>
  );
};
