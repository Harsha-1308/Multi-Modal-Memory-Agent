import React, { useState } from 'react';
import { Database, Shield, Zap, Sparkles, Brain, ArrowRight } from 'lucide-react';

interface LandingPageProps {
  onGetStarted: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onGetStarted }) => {
  const [isTransitioning, setIsTransitioning] = useState(false);

  const handleClickGetStarted = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      onGetStarted();
    }, 280);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: 'radial-gradient(ellipse at 50% 15%, #faf6ee 0%, #ece5d6 85%)',
        color: 'var(--text-primary)',
        opacity: isTransitioning ? 0 : 1,
        transform: isTransitioning ? 'scale(0.98)' : 'scale(1)',
        transition: 'opacity 0.28s ease, transform 0.28s ease',
      }}
    >
      {/* Navbar (Only Clean Brand Logo, no extra Workspace button) */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '24px 48px',
          borderBottom: '1px solid var(--border-subtle)',
          backgroundColor: 'rgba(245, 241, 232, 0.7)',
          backdropFilter: 'blur(8px)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-light))',
              padding: '10px',
              borderRadius: '12px',
              display: 'flex',
              boxShadow: '0 4px 14px rgba(77, 99, 59, 0.3)',
            }}
          >
            <Brain size={24} color="#ffffff" />
          </div>
          <span style={{ fontSize: '20px', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
            Project Memory Agent
          </span>
        </div>
      </header>

      {/* Hero Section */}
      <main
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          padding: '60px 24px',
          maxWidth: '1000px',
          margin: '0 auto',
        }}
        className="fade-in"
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            background: 'var(--accent-subtle)',
            border: '1px solid rgba(77, 99, 59, 0.3)',
            padding: '6px 18px',
            borderRadius: '24px',
            color: 'var(--accent-primary)',
            fontSize: '13px',
            fontWeight: 600,
            marginBottom: '28px',
          }}
        >
          <Sparkles size={14} /> Production Project-Scoped AI Memory
        </div>

        <h1
          style={{
            fontSize: 'clamp(40px, 6vw, 64px)',
            fontWeight: 800,
            letterSpacing: '-0.03em',
            lineHeight: 1.1,
            marginBottom: '24px',
            color: 'var(--text-primary)',
          }}
        >
          Project Memory Agent
        </h1>

        <p
          style={{
            fontSize: 'clamp(18px, 2.5vw, 22px)',
            color: 'var(--text-secondary)',
            maxWidth: '740px',
            lineHeight: 1.6,
            marginBottom: '40px',
            fontWeight: 400,
          }}
        >
          A project-scoped AI assistant that remembers, reasons from project context, and can show the evidence behind its answers.
        </p>

        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', justifyContent: 'center' }}>
          <button
            onClick={handleClickGetStarted}
            style={{
              background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-hover))',
              color: '#ffffff',
              padding: '16px 40px',
              borderRadius: '12px',
              fontSize: '17px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              boxShadow: '0 8px 24px rgba(77, 99, 59, 0.35)',
              transform: 'translateY(0)',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 10px 28px rgba(77, 99, 59, 0.45)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 8px 24px rgba(77, 99, 59, 0.35)';
            }}
          >
            Get Started <ArrowRight size={20} />
          </button>
        </div>

        {/* Feature Cards Grid (Beige & Olive) */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '24px',
            width: '100%',
            marginTop: '70px',
            textAlign: 'left',
          }}
        >
          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '16px',
              padding: '28px',
              boxShadow: '0 4px 20px rgba(0,0,0,0.03)',
            }}
          >
            <div
              style={{
                background: 'var(--accent-subtle)',
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px',
                border: '1px solid rgba(77, 99, 59, 0.2)',
              }}
            >
              <Shield size={22} color="var(--accent-primary)" />
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px', color: 'var(--text-primary)' }}>
              Absolute Project Isolation
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.6 }}>
              Each project owns exactly one dedicated Hindsight bank. Memory never leaks across projects.
            </p>
          </div>

          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '16px',
              padding: '28px',
              boxShadow: '0 4px 20px rgba(0,0,0,0.03)',
            }}
          >
            <div
              style={{
                background: 'var(--accent-subtle)',
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px',
                border: '1px solid rgba(77, 99, 59, 0.2)',
              }}
            >
              <Database size={22} color="var(--accent-primary)" />
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px', color: 'var(--text-primary)' }}>
              Dual-Layer Evidence
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.6 }}>
              Original files are stored securely with SHA-256 hashes, paired with rich Groq vision and document analysis.
            </p>
          </div>

          <div
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '16px',
              padding: '28px',
              boxShadow: '0 4px 20px rgba(0,0,0,0.03)',
            }}
          >
            <div
              style={{
                background: 'var(--accent-subtle)',
                width: '44px',
                height: '44px',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '16px',
                border: '1px solid rgba(77, 99, 59, 0.2)',
              }}
            >
              <Zap size={22} color="var(--accent-primary)" />
            </div>
            <h3 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '8px', color: 'var(--text-primary)' }}>
              Memory ON / OFF Toggle
            </h3>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px', lineHeight: 1.6 }}>
              Toggle instant retrieval without losing memory bank data. Chat history is preserved per conversation.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer
        style={{
          textAlign: 'center',
          padding: '24px',
          color: 'var(--text-muted)',
          fontSize: '13px',
          borderTop: '1px solid var(--border-subtle)',
        }}
      >
        Project Memory Agent • Powered by Hindsight & Groq
      </footer>
    </div>
  );
};
