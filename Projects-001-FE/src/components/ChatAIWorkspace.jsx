import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  BrainCircuit,
  ClipboardList,
  Clock3,
  Database,
  FolderKanban,
  Layers3,
  LoaderCircle,
  MessageSquareText,
  RefreshCcw,
  Scale,
  SendHorizontal,
  Sparkles,
  WalletCards,
} from 'lucide-react';

const promptIconMap = {
  budget: AlertTriangle,
  cash: WalletCards,
  overdue: Clock3,
  compare: Scale,
  default: Sparkles,
};

const dataSignalIconMap = {
  boq: ClipboardList,
  transactions: WalletCards,
  approvals: Layers3,
  default: Database,
};

const hasItems = (items) => Array.isArray(items) && items.length > 0;

function PromptCard({ item, onClick, disabled, compact = false }) {
  const Icon = promptIconMap[item.kind] || promptIconMap.default;

  return (
    <button
      type="button"
      className={compact ? 'chat-ai-prompt-card compact' : 'chat-ai-prompt-card'}
      onClick={() => onClick(item.prompt)}
      disabled={disabled}
    >
      <span className="chat-ai-prompt-icon">
        <Icon size={17} />
      </span>
      <span>
        <strong>{item.title}</strong>
        <small>{item.description}</small>
      </span>
      <ArrowRight size={15} />
    </button>
  );
}

export function ChatAIHero({ selectedProject, messageCount, routeContextLabel, routeInitialPrompt }) {
  const focusLabel = selectedProject ? selectedProject.name : 'All projects';

  return (
    <section className="chat-ai-hero">
      <div className="chat-ai-hero-copy">
        <div className="chat-ai-kicker">
          <Sparkles size={15} />
          Executive AI
        </div>
        <h1>Chat AI</h1>
        <p>
          ถามเรื่องงบประมาณ cash flow ความเสี่ยง และภาพรวมโครงการจากข้อมูลในระบบ
        </p>
        {routeContextLabel ? (
          <div className="chat-ai-route-context">
            <FolderKanban size={15} />
            {routeContextLabel}
            {routeInitialPrompt ? ' พร้อม context ที่ส่งมาจากหน้าก่อนหน้า' : ''}
          </div>
        ) : null}
      </div>

      <div className="chat-ai-hero-rail" aria-label="Chat AI status">
        <div>
          <span>Scope</span>
          <strong>{focusLabel}</strong>
        </div>
        <div>
          <span>Thread</span>
          <strong>{messageCount.toLocaleString('en-US')} messages</strong>
        </div>
        <div>
          <span>Sources</span>
          <strong>BOQ / Cash / Queue</strong>
        </div>
      </div>
    </section>
  );
}

export function ChatNotice({ tone = 'neutral', children }) {
  return (
    <div className={`chat-ai-notice ${tone}`}>
      {children}
    </div>
  );
}

export function ChatContextBar({
  projects,
  projectId,
  onProjectChange,
  selectedProject,
  onClearConversation,
  isClearingHistory,
  canClear,
}) {
  return (
    <div className="chat-ai-context-bar">
      <div className="chat-ai-context-main">
        <label className="chat-ai-field">
          <span>Project Scope</span>
          <select value={projectId} onChange={(event) => onProjectChange(event.target.value)}>
            <option value="">ทุกโครงการ</option>
            {projects.map((item) => (
              <option key={item.project_id} value={item.project_id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>

        <span className={selectedProject ? 'chat-ai-scope-chip focused' : 'chat-ai-scope-chip'}>
          <FolderKanban size={14} />
          {selectedProject ? selectedProject.name : 'โหมดรวมทุกโครงการ'}
        </span>
      </div>

      <button
        type="button"
        className="chat-ai-button chat-ai-button-secondary"
        onClick={onClearConversation}
        disabled={isClearingHistory || !canClear}
      >
        <RefreshCcw size={16} className={isClearingHistory ? 'spin' : ''} />
        {isClearingHistory ? 'กำลังล้าง...' : 'ล้างบทสนทนา'}
      </button>
    </div>
  );
}

export function ChatEmptyState({ prompts, onPromptClick, disabled }) {
  return (
    <div className="chat-ai-empty-state">
      <div className="chat-ai-empty-head">
        <span className="chat-ai-empty-icon">
          <BrainCircuit size={22} />
        </span>
        <div>
          <h2>Decision Starters</h2>
          <p>เลือกคำถามเริ่มต้น หรือพิมพ์คำถามเองด้านล่าง</p>
        </div>
      </div>

      <div className="chat-ai-prompt-grid">
        {prompts.map((item) => (
          <PromptCard
            key={item.title}
            item={item}
            onClick={onPromptClick}
            disabled={disabled}
          />
        ))}
      </div>
    </div>
  );
}

export function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  const isError = message.tone === 'error';
  const hasSources = hasItems(message.sources);
  const hasMetrics = hasItems(message.metrics);
  const hasNextActions = hasItems(message.nextActions);
  const hasTimeScope = Boolean(message.timeScope?.label);
  const hasProjectLink = !isUser && message.projectId;
  const hasMetadata =
    !isUser &&
    (message.projectName ||
      message.contextItemCount ||
      hasSources ||
      hasMetrics ||
      hasNextActions ||
      hasTimeScope ||
      message.intent);

  return (
    <div className={isUser ? 'chat-ai-message-row is-user' : 'chat-ai-message-row'}>
      <article className={`chat-ai-message ${isUser ? 'is-user' : 'is-assistant'} ${isError ? 'is-error' : ''}`}>
        {!isUser ? (
          <div className="chat-ai-message-kicker">
            {isError ? <AlertTriangle size={14} /> : <Sparkles size={14} />}
            Chat AI
          </div>
        ) : null}

        <p className="chat-ai-message-text">{message.content}</p>

        {hasMetadata ? (
          <div className="chat-ai-answer-stack">
            <div className="chat-ai-meta-chips">
              {message.intent ? (
                <span>Intent: {message.intent.replace(/_/g, ' ')}</span>
              ) : null}
              {hasTimeScope ? (
                <span className="positive">Time: {message.timeScope.label}</span>
              ) : null}
              {message.projectName ? (
                <span>Scope: {message.projectName}</span>
              ) : null}
              {message.contextItemCount ? (
                <span>{message.contextItemCount} context items</span>
              ) : null}
            </div>

            {hasMetrics ? (
              <section className="chat-ai-answer-section">
                <div className="chat-ai-section-label">
                  <BarChart3 size={14} />
                  Key Metrics
                </div>
                <div className="chat-ai-metric-grid">
                  {message.metrics.map((metric) => (
                    <div key={metric.id} className="chat-ai-metric-card">
                      <span>{metric.label}</span>
                      <strong>{metric.value}</strong>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {hasTimeScope && (message.timeScope.startDate || message.timeScope.endDate) ? (
              <div className="chat-ai-time-scope">
                ช่วงข้อมูลที่ใช้วิเคราะห์: {message.timeScope.startDate || '-'} ถึง{' '}
                {message.timeScope.endDate || '-'}
              </div>
            ) : null}

            {hasSources ? (
              <section className="chat-ai-answer-section">
                <div className="chat-ai-section-label">
                  <Database size={14} />
                  Sources
                </div>
                <div className="chat-ai-source-list">
                  {message.sources.map((source) => (
                    <span key={source.id} title={source.description || source.label}>
                      {source.sheetName ? `${source.sheetName} · ` : ''}
                      {source.label}
                    </span>
                  ))}
                </div>
              </section>
            ) : null}

            {hasNextActions ? (
              <section className="chat-ai-answer-section">
                <div className="chat-ai-section-label">
                  <ArrowRight size={14} />
                  Next Actions
                </div>
                <div className="chat-ai-action-list">
                  {message.nextActions.map((action) => (
                    <div key={action.id}>{action.label}</div>
                  ))}
                </div>
              </section>
            ) : null}

            {hasProjectLink ? (
              <Link
                to={`/project/detail/${message.projectId}`}
                state={{
                  projectId: message.projectId,
                  projectName: message.projectName,
                }}
                className="chat-ai-inline-link"
              >
                เปิดหน้า Project Detail
                <ArrowRight size={14} />
              </Link>
            ) : null}
          </div>
        ) : null}
      </article>
    </div>
  );
}

export function ChatLoadingMessage() {
  return (
    <div className="chat-ai-message-row">
      <article className="chat-ai-message is-assistant is-loading">
        <LoaderCircle size={16} className="spin" />
        กำลังวิเคราะห์ข้อมูลและสร้างคำตอบ...
      </article>
    </div>
  );
}

export function ChatComposer({
  draftMessage,
  onDraftMessageChange,
  onSubmit,
  isSubmitting,
  composerError,
  selectedProject,
}) {
  const hasDraft = Boolean(draftMessage.trim());

  return (
    <form className="chat-ai-composer" onSubmit={onSubmit}>
      <textarea
        value={draftMessage}
        onChange={(event) => onDraftMessageChange(event.target.value)}
        placeholder="ถามเรื่องงบประมาณ, ความเสี่ยง, margin, cash flow หรือเจาะรายโครงการ..."
        rows={3}
        disabled={isSubmitting}
      />

      <div className="chat-ai-composer-footer">
        <div className={composerError ? 'chat-ai-composer-hint error' : 'chat-ai-composer-hint'}>
          {composerError ||
            (selectedProject
              ? `คำถามถัดไปจะอิงโครงการ ${selectedProject.name}`
              : 'หากยังไม่เลือกโครงการ คำตอบจะมองภาพรวมทั้งระบบ')}
        </div>

        <button
          type="submit"
          className="chat-ai-button chat-ai-button-primary"
          disabled={!hasDraft || isSubmitting}
        >
          {isSubmitting ? <LoaderCircle size={16} className="spin" /> : <SendHorizontal size={16} />}
          ส่งคำถาม
        </button>
      </div>
    </form>
  );
}

export function ChatAISidePanel({
  prompts,
  dataSignals,
  selectedProject,
  onPromptClick,
  isSubmitting,
}) {
  return (
    <aside className="chat-ai-side-panel">
      <section className="chat-ai-side-card">
        <div className="chat-ai-side-card-head">
          <span>
            <FolderKanban size={18} />
          </span>
          <div>
            <h2>Current Scope</h2>
            <p>{selectedProject ? 'Focused project' : 'Global analysis'}</p>
          </div>
        </div>

        <div className={selectedProject ? 'chat-ai-current-scope focused' : 'chat-ai-current-scope'}>
          <span>{selectedProject ? 'Project' : 'Scope'}</span>
          <strong>{selectedProject ? selectedProject.name : 'ทุกโครงการ'}</strong>
        </div>

        {selectedProject ? (
          <Link
            to={`/project/detail/${selectedProject.project_id}`}
            state={{
              projectId: selectedProject.project_id,
              projectName: selectedProject.name,
            }}
            className="chat-ai-inline-link"
          >
            เปิดหน้าโครงการนี้
            <ArrowRight size={14} />
          </Link>
        ) : null}
      </section>

      <section className="chat-ai-side-card">
        <div className="chat-ai-side-title">
          <MessageSquareText size={18} />
          Prompt Library
        </div>
        <div className="chat-ai-side-prompts">
          {prompts.map((item) => (
            <PromptCard
              key={item.title}
              item={item}
              onClick={onPromptClick}
              disabled={isSubmitting}
              compact
            />
          ))}
        </div>
      </section>

      <section className="chat-ai-side-card">
        <div className="chat-ai-side-title">
          <Database size={18} />
          Data Context
        </div>
        <div className="chat-ai-data-signal-list">
          {dataSignals.map((item) => {
            const Icon = dataSignalIconMap[item.kind] || dataSignalIconMap.default;
            return (
              <div key={item.title} className="chat-ai-data-signal">
                <span>
                  <Icon size={16} />
                </span>
                <div>
                  <strong>{item.title}</strong>
                  <small>{item.description}</small>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </aside>
  );
}
