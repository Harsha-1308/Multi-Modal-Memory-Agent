import React, { useState } from 'react';
import { X, Plus, Trash2, Loader2, FolderPlus } from 'lucide-react';
import { createProject } from '../api/client';
import type { Project } from '../api/client';

interface ProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (project: Project) => void;
}

export const ProjectModal: React.FC<ProjectModalProps> = ({
  isOpen,
  onClose,
  onProjectCreated,
}) => {
  const [name, setName] = useState('');
  const [projectType, setProjectType] = useState('code');
  const [description, setDescription] = useState('');
  const [seedMemories, setSeedMemories] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleAddSeed = () => {
    setSeedMemories([...seedMemories, '']);
  };

  const handleUpdateSeed = (index: number, val: string) => {
    const copy = [...seedMemories];
    copy[index] = val;
    setSeedMemories(copy);
  };

  const handleRemoveSeed = (index: number) => {
    setSeedMemories(seedMemories.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please provide a project name.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const validSeeds = seedMemories
        .map((text) => ({ text: text.trim() }))
        .filter((s) => s.text.length > 0);

      const project = await createProject({
        name: name.trim(),
        project_type: projectType.trim(),
        description: description.trim(),
        seed_memories: validSeeds.length > 0 ? validSeeds : undefined,
      });

      onProjectCreated(project);
      onClose();
      setName('');
      setDescription('');
      setSeedMemories([]);
    } catch (err: any) {
      setError(err?.message || 'Failed to create project. Please verify inputs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(31, 37, 27, 0.7)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
        padding: '16px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '560px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 40px rgba(0,0,0,0.15)',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '20px 24px',
            borderBottom: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-secondary)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                background: 'var(--accent-subtle)',
                padding: '8px',
                borderRadius: '8px',
                color: 'var(--accent-primary)',
                border: '1px solid rgba(77, 99, 59, 0.2)',
              }}
            >
              <FolderPlus size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)' }}>Create New Project</h2>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Initializes a dedicated, isolated Hindsight bank
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              color: 'var(--text-secondary)',
              padding: '6px',
              borderRadius: '6px',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Form Body */}
        <form
          onSubmit={handleSubmit}
          style={{
            padding: '24px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '18px',
            backgroundColor: 'var(--bg-card)',
          }}
        >
          {error && (
            <div
              style={{
                backgroundColor: 'rgba(185, 28, 28, 0.1)',
                border: '1px solid rgba(185, 28, 28, 0.25)',
                borderRadius: '8px',
                padding: '12px 16px',
                color: 'var(--danger)',
                fontSize: '13px',
              }}
            >
              {error}
            </div>
          )}

          <div>
            <label
              style={{
                display: 'block',
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--text-primary)',
                marginBottom: '6px',
              }}
            >
              Project Name *
            </label>
            <input
              type="text"
              placeholder="e.g. Frontend Investigation"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-card-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: 'var(--text-primary)',
                fontSize: '14px',
              }}
              required
            />
          </div>

          <div>
            <label
              style={{
                display: 'block',
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--text-primary)',
                marginBottom: '6px',
              }}
            >
              Project Type
            </label>
            <select
              value={projectType}
              onChange={(e) => setProjectType(e.target.value)}
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-card-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: 'var(--text-primary)',
                fontSize: '14px',
              }}
            >
              <option value="code">Code / Software Engineering</option>
              <option value="devops">DevOps / Cloud Architecture</option>
              <option value="research">Research & Data Analysis</option>
              <option value="general">General AI Workspace</option>
            </select>
          </div>

          <div>
            <label
              style={{
                display: 'block',
                fontSize: '13px',
                fontWeight: 600,
                color: 'var(--text-primary)',
                marginBottom: '6px',
              }}
            >
              Description
            </label>
            <textarea
              placeholder="Describe the project goal, scope, or current problem..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              style={{
                width: '100%',
                backgroundColor: 'var(--bg-card-subtle)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: 'var(--text-primary)',
                fontSize: '14px',
                resize: 'vertical',
              }}
            />
          </div>

          {/* Seed Memories Section */}
          <div style={{ marginTop: '6px' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '8px',
              }}
            >
              <div>
                <span
                  style={{
                    fontSize: '13px',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                  }}
                >
                  Seed Memories (Optional)
                </span>
                <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Initial facts to prime the project's Hindsight bank
                </p>
              </div>
              <button
                type="button"
                onClick={handleAddSeed}
                style={{
                  background: 'var(--accent-subtle)',
                  color: 'var(--accent-primary)',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  border: '1px solid rgba(77, 99, 59, 0.2)',
                }}
              >
                <Plus size={14} /> Add Seed
              </button>
            </div>

            {seedMemories.length === 0 ? (
              <div
                style={{
                  border: '1.5px dashed var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '16px',
                  textAlign: 'center',
                  color: 'var(--text-muted)',
                  fontSize: '12px',
                  backgroundColor: 'rgba(0,0,0,0.01)',
                }}
              >
                Zero seed memories required. You can add facts later dynamically during chat.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {seedMemories.map((text, idx) => (
                  <div
                    key={idx}
                    style={{ display: 'flex', gap: '8px', alignItems: 'center' }}
                  >
                    <input
                      type="text"
                      placeholder={`Seed fact #${idx + 1}...`}
                      value={text}
                      onChange={(e) => handleUpdateSeed(idx, e.target.value)}
                      style={{
                        flex: 1,
                        backgroundColor: 'var(--bg-card-subtle)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '6px',
                        padding: '8px 12px',
                        color: 'var(--text-primary)',
                        fontSize: '13px',
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => handleRemoveSeed(idx)}
                      style={{
                        background: 'transparent',
                        color: 'var(--danger)',
                        padding: '6px',
                        borderRadius: '6px',
                      }}
                      title="Remove seed"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: '12px',
              marginTop: '12px',
            }}
          >
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              style={{
                background: 'transparent',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                padding: '10px 18px',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 600,
              }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{
                background: 'var(--accent-primary)',
                color: '#fff',
                padding: '10px 24px',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                opacity: loading ? 0.7 : 1,
                boxShadow: '0 4px 12px rgba(77, 99, 59, 0.25)',
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Creating Bank...
                </>
              ) : (
                'Create Project'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
