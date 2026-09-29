import React from 'react';
import { Plus, MessageSquare, Folder, Brain, BookOpen, PanelLeftClose } from 'lucide-react';
import type { Project, Chat } from '../api/client';

interface SidebarProps {
  isOpen: boolean;
  projects: Project[];
  activeProjectId?: string;
  chats: Chat[];
  activeChatId?: string;
  onSelectProject: (projectId: string) => void;
  onSelectChat: (chatId: string) => void;
  onOpenProjectModal: () => void;
  onOpenChatModal: () => void;
  onOpenMemoriesModal: () => void;
  onCloseSidebar: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  projects,
  activeProjectId,
  chats,
  activeChatId,
  onSelectProject,
  onSelectChat,
  onOpenProjectModal,
  onOpenChatModal,
  onOpenMemoriesModal,
  onCloseSidebar,
}) => {
  return (
    <aside
      style={{
        width: isOpen ? '280px' : '0px',
        minWidth: isOpen ? '280px' : '0px',
        height: '100vh',
        backgroundColor: 'var(--bg-secondary)',
        borderRight: isOpen ? '1px solid var(--border-subtle)' : 'none',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 30,
        position: 'relative',
        transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        overflow: 'hidden',
      }}
    >
      <div style={{ width: '280px', display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* App Title & Collapse Header */}
        <div
          style={{
            padding: '16px 18px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'rgba(234, 228, 213, 0.8)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-light))',
                padding: '6px',
                borderRadius: '8px',
                display: 'flex',
                boxShadow: '0 2px 6px rgba(77, 99, 59, 0.3)',
              }}
            >
              <Brain size={18} color="#fff" />
            </div>
            <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
              Project Memory
            </span>
          </div>

          <button
            onClick={onCloseSidebar}
            style={{
              background: 'transparent',
              color: 'var(--text-secondary)',
              padding: '6px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
            }}
            title="Collapse sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
        </div>

        {/* Projects & Chats List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 12px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0 8px 8px 8px',
            }}
          >
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: 'var(--text-muted)',
              }}
            >
              Projects
            </span>
            <button
              onClick={onOpenProjectModal}
              style={{
                background: 'var(--accent-subtle)',
                color: 'var(--accent-primary)',
                padding: '4px 8px',
                borderRadius: '6px',
                fontSize: '11px',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                border: '1px solid rgba(77, 99, 59, 0.2)',
              }}
            >
              <Plus size={13} /> Project
            </button>
          </div>

          {projects.length === 0 ? (
            <div
              style={{
                textAlign: 'center',
                padding: '24px 12px',
                color: 'var(--text-muted)',
                fontSize: '12px',
              }}
            >
              No projects yet. Click "+ Project" to create one.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {projects.map((proj) => {
                const isSelected = proj.project_id === activeProjectId;
                return (
                  <div key={proj.project_id} style={{ display: 'flex', flexDirection: 'column' }}>
                    <button
                      onClick={() => onSelectProject(proj.project_id)}
                      style={{
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '8px 10px',
                        borderRadius: '8px',
                        backgroundColor: isSelected ? 'var(--bg-card)' : 'transparent',
                        border: isSelected ? '1px solid var(--border-active)' : '1px solid transparent',
                        color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                        textAlign: 'left',
                        boxShadow: isSelected ? '0 1px 4px rgba(0,0,0,0.06)' : 'none',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          overflow: 'hidden',
                        }}
                      >
                        <Folder size={15} color={isSelected ? 'var(--accent-primary)' : '#74806a'} />
                        <span
                          style={{
                            fontSize: '13px',
                            fontWeight: isSelected ? 600 : 500,
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {proj.name}
                        </span>
                      </div>
                      <span
                        style={{
                          fontSize: '10px',
                          color: 'var(--text-muted)',
                          backgroundColor: 'rgba(0,0,0,0.04)',
                          padding: '1px 5px',
                          borderRadius: '4px',
                          border: '1px solid var(--border-subtle)',
                        }}
                      >
                        {proj.project_type}
                      </span>
                    </button>

                    {/* Expandable Chats Under Active Project */}
                    {isSelected && (
                      <div
                        style={{
                          paddingLeft: '14px',
                          marginTop: '4px',
                          marginBottom: '8px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '2px',
                          borderLeft: '2px solid var(--border-subtle)',
                          marginLeft: '14px',
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '4px 6px',
                          }}
                        >
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 500 }}>
                            Chats
                          </span>
                          <button
                            onClick={onOpenChatModal}
                            style={{
                              background: 'transparent',
                              color: 'var(--accent-primary)',
                              fontSize: '11px',
                              fontWeight: 600,
                              display: 'flex',
                              alignItems: 'center',
                              gap: '2px',
                              padding: '2px 4px',
                            }}
                          >
                            <Plus size={11} /> Chat
                          </button>
                        </div>

                        {chats.length === 0 ? (
                          <div
                            style={{
                              fontSize: '11px',
                              color: 'var(--text-muted)',
                              padding: '6px',
                            }}
                          >
                            No chats yet. Click "+ Chat".
                          </div>
                        ) : (
                          chats.map((c) => {
                            const isChatActive = c.chat_id === activeChatId;
                            return (
                              <button
                                key={c.chat_id}
                                onClick={() => onSelectChat(c.chat_id)}
                                style={{
                                  width: '100%',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '8px',
                                  padding: '6px 8px',
                                  borderRadius: '6px',
                                  backgroundColor: isChatActive ? 'var(--bg-card)' : 'transparent',
                                  border: isChatActive ? '1px solid var(--border-subtle)' : '1px solid transparent',
                                  color: isChatActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                                  fontSize: '12.5px',
                                  textAlign: 'left',
                                  fontWeight: isChatActive ? 600 : 400,
                                }}
                              >
                                <MessageSquare
                                  size={13}
                                  color={isChatActive ? 'var(--accent-primary)' : 'var(--text-muted)'}
                                />
                                <span
                                  style={{
                                    whiteSpace: 'nowrap',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                  }}
                                >
                                  {c.name}
                                </span>
                              </button>
                            );
                          })
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer: View Bank Memories */}
        {activeProjectId && (
          <div
            style={{
              padding: '14px 16px',
              borderTop: '1px solid var(--border-subtle)',
              backgroundColor: 'rgba(234, 228, 213, 0.5)',
            }}
          >
            <button
              onClick={onOpenMemoriesModal}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                padding: '8px 12px',
                borderRadius: '8px',
                backgroundColor: 'var(--accent-subtle)',
                color: 'var(--accent-primary)',
                fontSize: '12px',
                fontWeight: 600,
                border: '1px solid rgba(77, 99, 59, 0.25)',
              }}
            >
              <BookOpen size={14} /> View Project Memories
            </button>
          </div>
        )}
      </div>
    </aside>
  );
};
