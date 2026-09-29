import React, { useEffect, useState, useRef } from 'react';
import type { Project, Chat, Message, EvidenceItem } from '../api/client';
import {
  getProjects,
  getChats,
  getMessages,
  sendMessage,
  updateChatSettings,
} from '../api/client';
import { Sidebar } from './Sidebar';
import { ChatHeader } from './ChatHeader';
import { MessageBubble } from './MessageBubble';
import { Composer } from './Composer';
import { ProjectModal } from './ProjectModal';
import { ChatModal } from './ChatModal';
import { MemoriesModal } from './MemoriesModal';
import { EvidenceLightbox } from './EvidenceLightbox';
import { RightSidebar } from './RightSidebar';
import { Brain, MessageSquarePlus, Sparkles, AlertCircle } from 'lucide-react';

export const Workspace: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState<string | undefined>();
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | undefined>();
  const [messages, setMessages] = useState<Message[]>([]);

  // Sidebar visibility
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Modals state
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [isChatModalOpen, setIsChatModalOpen] = useState(false);
  const [isMemoriesModalOpen, setIsMemoriesModalOpen] = useState(false);
  const [lightboxEvidence, setLightboxEvidence] = useState<EvidenceItem | null>(null);

  // Thinking / loading state
  const [isSending, setIsSending] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [memoryRefreshKey, setMemoryRefreshKey] = useState(0);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync with URL query parameters for refresh safety (Section 36)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const projId = params.get('project');
    const chId = params.get('chat');

    loadInitialData(projId || undefined, chId || undefined);
  }, []);

  const updateUrlParams = (projectId?: string, chatId?: string) => {
    const params = new URLSearchParams();
    if (projectId) params.set('project', projectId);
    if (chatId) params.set('chat', chatId);
    const newRelativePathQuery = window.location.pathname + '?' + params.toString();
    window.history.replaceState(null, '', newRelativePathQuery);
  };

  const loadInitialData = async (preferredProjId?: string, preferredChatId?: string) => {
    try {
      const projs = await getProjects();
      setProjects(projs);

      if (projs.length > 0) {
        const targetProj = projs.find((p) => p.project_id === preferredProjId) || projs[0];
        setActiveProjectId(targetProj.project_id);

        const projectChats = await getChats(targetProj.project_id);
        setChats(projectChats);

        if (projectChats.length > 0) {
          const targetChat =
            projectChats.find((c) => c.chat_id === preferredChatId) || projectChats[0];
          setActiveChatId(targetChat.chat_id);
          updateUrlParams(targetProj.project_id, targetChat.chat_id);
          loadChatMessages(targetChat.chat_id);
        } else {
          setActiveChatId(undefined);
          setMessages([]);
          updateUrlParams(targetProj.project_id);
        }
      }
    } catch (err: any) {
      setErrorBanner('Failed to connect to backend API: ' + (err?.message || 'Check server status'));
    }
  };

  const loadChatMessages = async (chatId: string) => {
    try {
      const msgs = await getMessages(chatId);
      setMessages(msgs);
      scrollToBottom();
    } catch (err: any) {
      console.error('Failed to load chat messages:', err);
    }
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, 80);
  };

  const handleSelectProject = async (projectId: string) => {
    setActiveProjectId(projectId);
    try {
      const projectChats = await getChats(projectId);
      setChats(projectChats);
      if (projectChats.length > 0) {
        setActiveChatId(projectChats[0].chat_id);
        updateUrlParams(projectId, projectChats[0].chat_id);
        loadChatMessages(projectChats[0].chat_id);
      } else {
        setActiveChatId(undefined);
        setMessages([]);
        updateUrlParams(projectId);
      }
    } catch (err: any) {
      setErrorBanner('Failed to load chats for project: ' + err?.message);
    }
  };

  const handleSelectChat = (chatId: string) => {
    setActiveChatId(chatId);
    updateUrlParams(activeProjectId, chatId);
    loadChatMessages(chatId);
  };

  const handleToggleMemory = async (enabled: boolean) => {
    if (!activeChatId) return;
    try {
      const updatedChat = await updateChatSettings(activeChatId, { memory_enabled: enabled });
      setChats((prev) => prev.map((c) => (c.chat_id === activeChatId ? updatedChat : c)));
    } catch (err: any) {
      setErrorBanner('Failed to toggle memory: ' + err?.message);
    }
  };

  const handleSendMessage = async (
    content: string,
    files: File[],
    descriptions: { index: number; description: string }[]
  ) => {
    if (!activeChatId) return;
    setErrorBanner(null);

    // Optimistically add user message to list
    const tempUserMsg: Message = {
      message_id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);
    setIsSending(true);
    scrollToBottom();

    try {
      const res = await sendMessage(activeChatId, content, files, descriptions);

      // Assistant response from backend
      const assistantMsg: Message = {
        message_id: res.message.message_id,
        role: 'assistant',
        content: res.message.content,
        created_at: res.message.created_at,
        metadata: {
          memory_enabled: res.memory.enabled,
          evidence: res.evidence,
          attachments: res.attachments,
        },
      };

      setMessages((prev) => [...prev, assistantMsg]);
      setMemoryRefreshKey((key) => key + 1);
      scrollToBottom();
    } catch (err: any) {
      setMessages((prev) => prev.filter((msg) => msg.message_id !== tempUserMsg.message_id));
      setErrorBanner(err?.message || 'Failed to send message.');
    } finally {
      setIsSending(false);
    }
  };

  const activeProject = projects.find((p) => p.project_id === activeProjectId);
  const activeChat = chats.find((c) => c.chat_id === activeChatId);
  const isMemoryActive = activeChat ? activeChat.memory_enabled : false;

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
        backgroundColor: isMemoryActive ? 'var(--bg-primary)' : 'var(--bg-primary-off)',
        transition: 'background-color 0.4s ease',
      }}
      className="fade-in"
    >
      {/* Full-Height Left Sidebar */}
      <Sidebar
        isOpen={isSidebarOpen}
        projects={projects}
        activeProjectId={activeProjectId}
        chats={chats}
        activeChatId={activeChatId}
        onSelectProject={handleSelectProject}
        onSelectChat={handleSelectChat}
        onOpenProjectModal={() => setIsProjectModalOpen(true)}
        onOpenChatModal={() => setIsChatModalOpen(true)}
        onOpenMemoriesModal={() => setIsMemoriesModalOpen(true)}
        onCloseSidebar={() => setIsSidebarOpen(false)}
      />

      {/* Central Chat Workspace */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
          backgroundColor: 'transparent',
          position: 'relative',
        }}
      >
        {/* Chat Header */}
        <ChatHeader
          project={activeProject}
          chat={activeChat}
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={() => setIsSidebarOpen(true)}
          onToggleMemory={handleToggleMemory}
        />

        {/* Global Error Banner if any */}
        {errorBanner && (
          <div
            style={{
              padding: '10px 20px',
              backgroundColor: 'rgba(185, 28, 28, 0.1)',
              borderBottom: '1px solid rgba(185, 28, 28, 0.25)',
              color: 'var(--danger)',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertCircle size={16} />
              <span>{errorBanner}</span>
            </div>
            <button
              onClick={() => setErrorBanner(null)}
              style={{ background: 'transparent', color: 'var(--danger)', fontSize: '12px' }}
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Messages Scroll Area */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {projects.length === 0 ? (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
                padding: '40px 20px',
                color: 'var(--text-muted)',
              }}
            >
              <Brain size={48} color="var(--accent-primary)" style={{ marginBottom: '16px', opacity: 0.7 }} />
              <h3 style={{ fontSize: '18px', color: 'var(--text-primary)', marginBottom: '8px', fontWeight: 600 }}>
                Welcome to Project Memory Agent
              </h3>
              <p style={{ maxWidth: '420px', fontSize: '14px', lineHeight: 1.6, marginBottom: '20px', color: 'var(--text-secondary)' }}>
                Get started by creating your first project workspace. Each project receives its own isolated Hindsight memory bank.
              </p>
              <button
                onClick={() => setIsProjectModalOpen(true)}
                style={{
                  backgroundColor: 'var(--accent-primary)',
                  color: '#fff',
                  padding: '10px 22px',
                  borderRadius: '8px',
                  fontWeight: 600,
                  fontSize: '14px',
                  boxShadow: '0 4px 12px rgba(77, 99, 59, 0.25)',
                }}
              >
                + Create First Project
              </button>
            </div>
          ) : !activeChat ? (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
                padding: '40px 20px',
                color: 'var(--text-muted)',
              }}
            >
              <MessageSquarePlus size={44} color="var(--accent-primary)" style={{ marginBottom: '14px', opacity: 0.7 }} />
              <h3 style={{ fontSize: '17px', color: 'var(--text-primary)', marginBottom: '6px', fontWeight: 600 }}>
                No active chat in {activeProject?.name}
              </h3>
              <p style={{ fontSize: '13px', marginBottom: '18px', color: 'var(--text-secondary)' }}>
                Create a chat to begin recording and querying this project's memories.
              </p>
              <button
                onClick={() => setIsChatModalOpen(true)}
                style={{
                  backgroundColor: 'var(--accent-primary)',
                  color: '#fff',
                  padding: '9px 18px',
                  borderRadius: '8px',
                  fontWeight: 600,
                  fontSize: '13px',
                }}
              >
                + Create Chat
              </button>
            </div>
          ) : messages.length === 0 && !isSending ? (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
                padding: '40px 20px',
                color: 'var(--text-muted)',
              }}
            >
              <Sparkles size={40} color="var(--accent-primary)" style={{ marginBottom: '14px', opacity: 0.8 }} />
              <h3 style={{ fontSize: '18px', color: 'var(--text-primary)', marginBottom: '6px', fontWeight: 600 }}>
                {activeChat.name}
              </h3>
              <p style={{ fontSize: '13.5px', maxWidth: '440px', lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                Memory is currently{' '}
                <span
                  style={{
                    color: activeChat.memory_enabled ? 'var(--accent-primary)' : 'var(--text-muted)',
                    fontWeight: 700,
                  }}
                >
                  {activeChat.memory_enabled ? 'ACTIVE' : 'DISABLED'}
                </span>
                . Send updates, upload error screenshots, or ask what happened previously.
              </p>
            </div>
          ) : (
            <div style={{ padding: '16px 0' }}>
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.message_id}
                  message={msg}
                  onOpenLightbox={(ev) => setLightboxEvidence(ev)}
                />
              ))}

              {/* Live Thinking Indicator */}
              {isSending && (
                <MessageBubble
                  message={{
                    message_id: 'thinking',
                    role: 'assistant',
                    content: '',
                    created_at: new Date().toISOString(),
                  }}
                  isThinking={true}
                />
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Composer */}
        {activeChat && (
          <Composer onSendMessage={handleSendMessage} disabled={isSending} />
        )}
      </div>

      {/* Right Sidebar (Memory & Context Partition) */}
      <RightSidebar
        isOpen={Boolean(activeChat)}
        memoryEnabled={Boolean(activeChat?.memory_enabled)}
        project={activeProject}
        refreshKey={memoryRefreshKey}
        onOpenMemoriesModal={() => setIsMemoriesModalOpen(true)}
      />

      {/* Modals */}
      <ProjectModal
        isOpen={isProjectModalOpen}
        onClose={() => setIsProjectModalOpen(false)}
        onProjectCreated={(newProject) => {
          setProjects([newProject, ...projects]);
          handleSelectProject(newProject.project_id);
        }}
      />

      {activeProject && (
        <ChatModal
          isOpen={isChatModalOpen}
          projectId={activeProject.project_id}
          projectName={activeProject.name}
          onClose={() => setIsChatModalOpen(false)}
          onChatCreated={(newChat) => {
            setChats([newChat, ...chats]);
            handleSelectChat(newChat.chat_id);
          }}
        />
      )}

      {activeProject && (
        <MemoriesModal
          isOpen={isMemoriesModalOpen}
          projectId={activeProject.project_id}
          projectName={activeProject.name}
          onClose={() => setIsMemoriesModalOpen(false)}
        />
      )}

      <EvidenceLightbox
        evidence={lightboxEvidence}
        onClose={() => setLightboxEvidence(null)}
      />
    </div>
  );
};
