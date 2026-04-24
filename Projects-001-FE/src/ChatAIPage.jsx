import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  ArrowRight,
  BarChart3,
  BrainCircuit,
  Database,
  FolderKanban,
  LoaderCircle,
  RefreshCcw,
  Sparkles,
} from 'lucide-react';
import Loading from './components/Loading';
import { askChatQuestion, clearChatHistory, getChatHistory, getInputProjectOptions } from './api';

const SUGGESTED_PROMPTS = [
  {
    title: 'Budget Risk',
    description: 'หาโครงการหรืองานที่มีแนวโน้มใช้งบเกิน',
    prompt: 'สรุปความเสี่ยงงบบานปลายจากข้อมูลที่มีอยู่ พร้อมบอกประเด็นที่ควรตรวจต่อ',
  },
  {
    title: 'Cash Flow',
    description: 'มองภาพรวมรายรับรายจ่ายและคิวอนุมัติ',
    prompt: 'สรุปภาพรวม cash flow ปัจจุบัน และระบุจุดที่กระทบสภาพคล่องมากที่สุด',
  },
  {
    title: 'Overdue',
    description: 'เน้นหายอดค้างและงานที่ควรถูกเร่งรัด',
    prompt: 'มีรายการ overdue หรือคิวที่ควรเร่งจัดการอะไรบ้าง',
  },
  {
    title: 'Material vs Labor',
    description: 'เปรียบเทียบต้นทุนวัสดุกับค่าแรง',
    prompt: 'เปรียบเทียบค่าแรงกับค่าวัสดุจากข้อมูลล่าสุด และชี้รายการที่ผิดปกติ',
  },
];

const STRATEGY_PILLARS = [
  {
    icon: BrainCircuit,
    title: 'Strategic Q&A',
    description: 'ถามเชิงผู้บริหาร เช่น margin, cost overrun, cash flow และ project risk',
  },
  {
    icon: Database,
    title: 'Grounded Answers',
    description: 'คำตอบควรอิง BOQ, transaction, approval queue และเอกสารประกอบ ไม่ใช่ตอบลอย',
  },
  {
    icon: BarChart3,
    title: 'Actionable Insight',
    description: 'ทุกคำตอบควรพาไปสู่ next action เช่น เปิดโครงการ ดู approval queue หรือเช็ก source',
  },
];

const makeMessageId = () =>
  `msg-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;

const getErrorMessage = (error) =>
  error?.message || 'Unable to get an answer from Chat AI right now.';

const MAX_PERSISTED_EXCHANGES = 20;
const MAX_VISIBLE_MESSAGES = MAX_PERSISTED_EXCHANGES * 2;

const trimMessages = (items) => items.slice(-MAX_VISIBLE_MESSAGES);

const historyToMessages = (historyItems) =>
  trimMessages(
    historyItems.flatMap((item) => {
      const messages = [];
      const question = String(item.question || '').trim();

      if (question) {
        messages.push({
          id: `${item.id}-user`,
          role: 'user',
          content: question,
        });
      }

      messages.push({
        id: `${item.id}-assistant`,
        role: 'assistant',
        content: item.reply,
        summary: item.summary,
        intent: item.intent,
        metrics: item.metrics,
        nextActions: item.nextActions,
        timeScope: item.timeScope,
        sources: item.sources,
        projectId: item.projectId,
        projectName: item.projectName,
        contextItemCount: item.contextItemCount,
      });

      return messages;
    })
  );

function ChatAIPage() {
  const location = useLocation();
  const routeProjectId = String(location.state?.projectId || '').trim();
  const routeProjectName = String(location.state?.projectName || '').trim();
  const routeInitialPrompt = String(location.state?.initialPrompt || '').trim();
  const routeContextLabel = String(location.state?.contextLabel || '').trim();
  const routeAutoSubmit = Boolean(location.state?.autoSubmit);

  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState(routeProjectId);
  const [draftMessage, setDraftMessage] = useState(routeInitialPrompt);
  const [messages, setMessages] = useState([]);
  const [pageError, setPageError] = useState('');
  const [composerError, setComposerError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isClearingHistory, setIsClearingHistory] = useState(false);

  const messagesEndRef = useRef(null);
  const hasConsumedInitialPromptRef = useRef(false);

  const selectedProject =
    projects.find((item) => item.project_id === projectId) ||
    (routeProjectId
      ? {
          project_id: routeProjectId,
          name: routeProjectName || 'Current Project',
        }
      : null);

  useEffect(() => {
    let isMounted = true;

    const loadInitialData = async () => {
      setLoading(true);
      setPageError('');

      const [projectsResult, historyResult] = await Promise.allSettled([
        getInputProjectOptions(),
        getChatHistory(),
      ]);

      if (!isMounted) return;

      const errors = [];

      if (projectsResult.status === 'fulfilled') {
        setProjects(projectsResult.value);
      } else {
        errors.push(projectsResult.reason?.message || 'Failed to load project scope options.');
      }

      if (historyResult.status === 'fulfilled') {
        setMessages(historyToMessages(historyResult.value));
      } else {
        errors.push(historyResult.reason?.message || 'Failed to load chat history.');
      }

      setPageError(errors.join(' '));
      setLoading(false);
    };

    loadInitialData();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isSubmitting]);

  const submitQuestion = async (rawMessage) => {
    const message = String(rawMessage || '').trim();
    if (!message || isSubmitting) return;

    const nextUserMessage = {
      id: makeMessageId(),
      role: 'user',
      content: message,
    };

    setMessages((current) => trimMessages([...current, nextUserMessage]));
    setDraftMessage('');
    setComposerError('');
    setIsSubmitting(true);

    try {
      const response = await askChatQuestion({
        message,
        projectId,
      });

      const nextAssistantMessage = {
        id: makeMessageId(),
        role: 'assistant',
        content: response.reply,
        summary: response.summary,
        intent: response.intent,
        metrics: response.metrics,
        nextActions: response.nextActions,
        timeScope: response.timeScope,
        sources: response.sources,
        projectId: response.projectId || projectId,
        projectName: response.projectName || selectedProject?.name || '',
        contextItemCount: response.contextItemCount,
      };

      setMessages((current) => trimMessages([...current, nextAssistantMessage]));
    } catch (error) {
      const messageText = getErrorMessage(error);
      setComposerError(messageText);
      setMessages((current) =>
        trimMessages([
          ...current,
          {
            id: makeMessageId(),
            role: 'assistant',
            tone: 'error',
            content: messageText,
            summary: '',
            intent: '',
            metrics: [],
            nextActions: [],
            timeScope: null,
            sources: [],
            projectId,
            projectName: selectedProject?.name || '',
            contextItemCount: 0,
          },
        ])
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleComposerSubmit = async (event) => {
    event.preventDefault();
    await submitQuestion(draftMessage);
  };

  const handlePromptClick = async (prompt) => {
    await submitQuestion(prompt);
  };

  const clearConversation = async () => {
    if (isClearingHistory || (!messages.length && !composerError)) return;

    try {
      setIsClearingHistory(true);
      setComposerError('');
      setPageError('');
      await clearChatHistory();
      setMessages([]);
    } catch (error) {
      setComposerError(error.message || 'Failed to clear chat history.');
    } finally {
      setIsClearingHistory(false);
    }
  };

  useEffect(() => {
    if (!routeInitialPrompt) return;
    setDraftMessage(routeInitialPrompt);
  }, [routeInitialPrompt]);

  useEffect(() => {
    hasConsumedInitialPromptRef.current = false;
    setProjectId(routeProjectId);
  }, [routeInitialPrompt, routeProjectId]);

  useEffect(() => {
    if (!routeAutoSubmit || !routeInitialPrompt || loading || isSubmitting || hasConsumedInitialPromptRef.current) {
      return;
    }

    hasConsumedInitialPromptRef.current = true;
    submitQuestion(routeInitialPrompt);
  }, [isSubmitting, loading, routeAutoSubmit, routeInitialPrompt]);

  if (loading) return <Loading />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '20px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <h1 style={{ fontSize: '32px', margin: 0 }}>Chat AI</h1>
          <p style={{ margin: 0, color: '#6b7280', fontSize: '15px', maxWidth: '720px' }}>
            Executive assistant สำหรับสรุปภาพรวมโครงการ ค้นหาความเสี่ยง และตอบคำถามเชิงกลยุทธ์จากข้อมูลในระบบ
          </p>
        </div>

        <div
          style={{
            minWidth: '280px',
            padding: '18px 20px',
            borderRadius: '20px',
            background: 'linear-gradient(135deg, rgba(196,164,112,0.16), rgba(255,255,255,0.9))',
            border: '1px solid rgba(196,164,112,0.35)',
            boxShadow: '0 10px 30px rgba(61,64,58,0.08)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
            <Sparkles size={18} color="#8b6d3f" />
            <span style={{ fontSize: '13px', fontWeight: 700, color: '#8b6d3f', letterSpacing: '0.04em' }}>
              AI STRATEGIC SCOPE
            </span>
          </div>
          <p style={{ margin: 0, color: '#3d403a', fontSize: '14px', lineHeight: 1.6 }}>
            ควรใช้หน้านี้ถามเรื่องงบประมาณ ต้นทุนจริง คิวอนุมัติ และภาพรวมที่ผู้บริหารต้องตัดสินใจต่อ
          </p>
        </div>
      </div>

      {pageError ? (
        <div
          className="card"
          style={{
            borderColor: '#f3c7c3',
            backgroundColor: '#fff7f7',
            color: '#a53d35',
            padding: '16px 20px',
          }}
        >
          {pageError}
        </div>
      ) : null}

      {routeContextLabel ? (
        <div
          className="card"
          style={{
            borderColor: '#eadfce',
            backgroundColor: '#faf7f1',
            color: '#5f4b27',
            padding: '14px 18px',
          }}
        >
          {routeContextLabel}
          {routeInitialPrompt ? ' พร้อม context ที่ส่งมาจากหน้าก่อนหน้า' : ''}
        </div>
      ) : null}

      <div className="chat-ai-layout">
        <section
          className="card"
          style={{
            padding: '0',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            minHeight: '720px',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px',
              flexWrap: 'wrap',
              padding: '24px',
              borderBottom: '1px solid #efe9dd',
              background:
                'linear-gradient(180deg, rgba(250,247,241,0.95) 0%, rgba(255,255,255,0.95) 100%)',
            }}
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <span style={{ fontSize: '13px', color: '#8b6d3f', fontWeight: 700, letterSpacing: '0.05em' }}>
                CHAT CONTEXT
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <select
                  value={projectId}
                  onChange={(event) => setProjectId(event.target.value)}
                  style={{
                    minWidth: '250px',
                    padding: '10px 14px',
                    borderRadius: '12px',
                    border: '1px solid #d8cfbf',
                    backgroundColor: '#faf7f1',
                    fontSize: '14px',
                    outline: 'none',
                    color: '#333',
                  }}
                >
                  <option value="">ทุกโครงการ</option>
                  {projects.map((item) => (
                    <option key={item.project_id} value={item.project_id}>
                      {item.name}
                    </option>
                  ))}
                </select>

                <span
                  style={{
                    padding: '8px 12px',
                    borderRadius: '999px',
                    backgroundColor: projectId ? 'rgba(39,165,122,0.12)' : 'rgba(61,64,58,0.08)',
                    color: projectId ? '#166b4f' : '#4b5563',
                    fontSize: '13px',
                    fontWeight: 600,
                  }}
                >
                  {selectedProject ? `กำลังโฟกัส: ${selectedProject.name}` : 'โหมดรวมทุกโครงการ'}
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={clearConversation}
              disabled={isClearingHistory || (!messages.length && !composerError)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 14px',
                borderRadius: '12px',
                border: '1px solid #ded4c2',
                backgroundColor: 'white',
                color: '#4b5563',
                cursor:
                  isClearingHistory || (!messages.length && !composerError) ? 'not-allowed' : 'pointer',
                opacity: isClearingHistory || (!messages.length && !composerError) ? 0.6 : 1,
                fontWeight: 600,
              }}
            >
              <RefreshCcw size={16} className={isClearingHistory ? 'spin' : ''} />
              {isClearingHistory ? 'กำลังล้างประวัติ...' : 'ล้างบทสนทนา'}
            </button>
          </div>

          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
              background:
                'radial-gradient(circle at top right, rgba(196,164,112,0.08), transparent 30%), #fff',
            }}
          >
            <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
              {messages.length === 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  <div
                    style={{
                      padding: '24px',
                      borderRadius: '24px',
                      backgroundColor: '#faf7f1',
                      border: '1px solid #ece3d4',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
                      <div
                        style={{
                          width: '42px',
                          height: '42px',
                          borderRadius: '14px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          backgroundColor: 'rgba(196,164,112,0.16)',
                          color: '#8b6d3f',
                        }}
                      >
                        <BrainCircuit size={20} />
                      </div>
                      <div>
                        <h2 style={{ margin: 0, fontSize: '22px' }}>ถามเชิงกลยุทธ์ได้ทันที</h2>
                        <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: '14px', lineHeight: 1.6 }}>
                          เริ่มจากคำถามภาพรวมก่อน แล้วค่อยเจาะลงรายโครงการ รายหมวดงาน หรือรายการที่ผิดปกติ
                        </p>
                      </div>
                    </div>

                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                        gap: '14px',
                      }}
                    >
                      {SUGGESTED_PROMPTS.map((item) => (
                        <button
                          key={item.title}
                          type="button"
                          onClick={() => handlePromptClick(item.prompt)}
                          disabled={isSubmitting}
                          style={{
                            textAlign: 'left',
                            padding: '18px',
                            borderRadius: '18px',
                            border: '1px solid #e2d8c6',
                            backgroundColor: 'white',
                            cursor: isSubmitting ? 'wait' : 'pointer',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '10px',
                            boxShadow: '0 8px 24px rgba(61,64,58,0.04)',
                          }}
                        >
                          <span style={{ fontWeight: 700, color: '#1f2937', fontSize: '15px' }}>{item.title}</span>
                          <span style={{ color: '#6b7280', fontSize: '13px', lineHeight: 1.5 }}>{item.description}</span>
                          <span style={{ color: '#8b6d3f', fontSize: '13px', fontWeight: 700 }}>ใช้ prompt นี้</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                  {messages.map((message) => {
                    const isUser = message.role === 'user';
                    const hasSources = Array.isArray(message.sources) && message.sources.length > 0;
                    const hasMetrics = Array.isArray(message.metrics) && message.metrics.length > 0;
                    const hasNextActions =
                      Array.isArray(message.nextActions) && message.nextActions.length > 0;
                    const hasTimeScope = Boolean(message.timeScope?.label);
                    const hasProjectLink = !isUser && message.projectId;

                    return (
                      <div
                        key={message.id}
                        style={{
                          display: 'flex',
                          justifyContent: isUser ? 'flex-end' : 'flex-start',
                        }}
                      >
                        <div
                          className="chat-ai-message"
                          style={{
                            backgroundColor: isUser
                              ? '#3d403a'
                              : message.tone === 'error'
                                ? '#fff6f5'
                                : '#faf7f1',
                            border: isUser
                              ? '1px solid transparent'
                              : message.tone === 'error'
                                ? '1px solid #f0c1bc'
                                : '1px solid #ece3d4',
                            color: isUser ? 'white' : '#1f2937',
                            boxShadow: isUser
                              ? '0 14px 30px rgba(61,64,58,0.16)'
                              : '0 10px 24px rgba(61,64,58,0.05)',
                          }}
                        >
                          {!isUser ? (
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '8px',
                                marginBottom: '10px',
                                color: message.tone === 'error' ? '#a53d35' : '#8b6d3f',
                                fontSize: '12px',
                                fontWeight: 700,
                                letterSpacing: '0.05em',
                              }}
                            >
                              <Sparkles size={14} />
                              CHAT AI
                            </div>
                          ) : null}

                          <p style={{ margin: 0, whiteSpace: 'pre-wrap', lineHeight: 1.75, fontSize: '15px' }}>
                            {message.content}
                          </p>

                          {!isUser &&
                          (message.projectName ||
                            message.contextItemCount ||
                            hasSources ||
                            hasMetrics ||
                            hasNextActions ||
                            hasTimeScope ||
                            message.intent) ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginTop: '16px' }}>
                              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                                {message.intent ? (
                                  <span
                                    style={{
                                      padding: '7px 10px',
                                      borderRadius: '999px',
                                      backgroundColor: 'rgba(139,109,63,0.12)',
                                      color: '#8b6d3f',
                                      fontSize: '12px',
                                      fontWeight: 700,
                                    }}
                                  >
                                    Intent: {message.intent.replace(/_/g, ' ')}
                                  </span>
                                ) : null}
                                {hasTimeScope ? (
                                  <span
                                    style={{
                                      padding: '7px 10px',
                                      borderRadius: '999px',
                                      backgroundColor: 'rgba(39,165,122,0.12)',
                                      color: '#166b4f',
                                      fontSize: '12px',
                                      fontWeight: 700,
                                    }}
                                  >
                                    Time: {message.timeScope.label}
                                  </span>
                                ) : null}
                                {message.projectName ? (
                                  <span
                                    style={{
                                      padding: '7px 10px',
                                      borderRadius: '999px',
                                      backgroundColor: 'rgba(61,64,58,0.08)',
                                      color: '#374151',
                                      fontSize: '12px',
                                      fontWeight: 600,
                                    }}
                                  >
                                    Scope: {message.projectName}
                                  </span>
                                ) : null}
                                {message.contextItemCount ? (
                                  <span
                                    style={{
                                      padding: '7px 10px',
                                      borderRadius: '999px',
                                      backgroundColor: 'rgba(196,164,112,0.14)',
                                      color: '#8b6d3f',
                                      fontSize: '12px',
                                      fontWeight: 700,
                                    }}
                                  >
                                    Context items: {message.contextItemCount}
                                  </span>
                                ) : null}
                              </div>

                              {hasMetrics ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#6b7280', letterSpacing: '0.05em' }}>
                                    KEY METRICS
                                  </span>
                                  <div
                                    style={{
                                      display: 'grid',
                                      gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
                                      gap: '10px',
                                    }}
                                  >
                                    {message.metrics.map((metric) => (
                                      <div
                                        key={metric.id}
                                        style={{
                                          padding: '12px',
                                          borderRadius: '14px',
                                          backgroundColor: 'white',
                                          border: '1px solid #eadfce',
                                          display: 'flex',
                                          flexDirection: 'column',
                                          gap: '6px',
                                        }}
                                      >
                                        <span style={{ fontSize: '12px', color: '#6b7280', fontWeight: 600 }}>
                                          {metric.label}
                                        </span>
                                        <span style={{ fontSize: '14px', color: '#1f2937', fontWeight: 700 }}>
                                          {metric.value}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ) : null}

                              {hasTimeScope && (message.timeScope.startDate || message.timeScope.endDate) ? (
                                <div
                                  style={{
                                    padding: '12px 14px',
                                    borderRadius: '14px',
                                    backgroundColor: 'rgba(39,165,122,0.08)',
                                    border: '1px solid rgba(39,165,122,0.18)',
                                    color: '#166b4f',
                                    fontSize: '13px',
                                    fontWeight: 600,
                                  }}
                                >
                                  ช่วงข้อมูลที่ใช้วิเคราะห์: {message.timeScope.startDate || '-'} ถึง{' '}
                                  {message.timeScope.endDate || '-'}
                                </div>
                              ) : null}

                              {hasSources ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#6b7280', letterSpacing: '0.05em' }}>
                                    SOURCES
                                  </span>
                                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                    {message.sources.map((source) => (
                                      <span
                                        key={source.id}
                                        title={source.description || source.label}
                                        style={{
                                          display: 'inline-flex',
                                          alignItems: 'center',
                                          gap: '6px',
                                          padding: '8px 10px',
                                          borderRadius: '12px',
                                          backgroundColor: 'white',
                                          border: '1px solid #eadfce',
                                          color: '#4b5563',
                                          fontSize: '12px',
                                          fontWeight: 600,
                                        }}
                                      >
                                        {source.sheetName ? `${source.sheetName} · ` : ''}
                                        {source.label}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              ) : null}

                              {hasNextActions ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                  <span style={{ fontSize: '12px', fontWeight: 700, color: '#6b7280', letterSpacing: '0.05em' }}>
                                    NEXT ACTIONS
                                  </span>
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                    {message.nextActions.map((action) => (
                                      <div
                                        key={action.id}
                                        style={{
                                          padding: '12px 14px',
                                          borderRadius: '14px',
                                          backgroundColor: 'rgba(196,164,112,0.1)',
                                          border: '1px solid rgba(196,164,112,0.18)',
                                          color: '#5f4b27',
                                          fontSize: '13px',
                                          fontWeight: 600,
                                          lineHeight: 1.6,
                                        }}
                                      >
                                        {action.label}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ) : null}

                              {hasProjectLink ? (
                                <Link
                                  to={`/project/detail/${message.projectId}`}
                                  state={{
                                    projectId: message.projectId,
                                    projectName: message.projectName,
                                  }}
                                  style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '8px',
                                    width: 'fit-content',
                                    color: '#8b6d3f',
                                    fontWeight: 700,
                                    textDecoration: 'none',
                                    fontSize: '13px',
                                  }}
                                >
                                  เปิดหน้า Project Detail
                                  <ArrowRight size={14} />
                                </Link>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    );
                  })}

                  {isSubmitting ? (
                    <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
                      <div
                        className="chat-ai-message"
                        style={{
                          backgroundColor: '#faf7f1',
                          border: '1px solid #ece3d4',
                          color: '#4b5563',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '10px',
                        }}
                      >
                        <LoaderCircle size={16} className="spin" />
                        กำลังวิเคราะห์ข้อมูลและสร้างคำตอบ...
                      </div>
                    </div>
                  ) : null}

                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>

            <div
              style={{
                padding: '20px 24px 24px',
                borderTop: '1px solid #efe9dd',
                backgroundColor: 'rgba(255,255,255,0.96)',
                backdropFilter: 'blur(10px)',
              }}
            >
              <form onSubmit={handleComposerSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <textarea
                  value={draftMessage}
                  onChange={(event) => setDraftMessage(event.target.value)}
                  placeholder="ถามเรื่องงบประมาณ, ความเสี่ยง, margin, cash flow หรือเจาะรายโครงการ..."
                  rows={3}
                  disabled={isSubmitting}
                  style={{
                    width: '100%',
                    borderRadius: '18px',
                    border: '1px solid #d8cfbf',
                    backgroundColor: '#faf7f1',
                    padding: '16px 18px',
                    resize: 'vertical',
                    minHeight: '110px',
                    outline: 'none',
                    fontSize: '15px',
                    lineHeight: 1.6,
                    color: '#1f2937',
                  }}
                />

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
                  <div style={{ color: composerError ? '#a53d35' : '#6b7280', fontSize: '13px' }}>
                    {composerError ||
                      (selectedProject
                        ? `คำถามถัดไปจะอิงโครงการ ${selectedProject.name}`
                        : 'หากยังไม่เลือกโครงการ คำตอบจะมองภาพรวมทั้งระบบ')}
                  </div>

                  <button
                    type="submit"
                    disabled={!draftMessage.trim() || isSubmitting}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '10px',
                      padding: '12px 16px',
                      borderRadius: '14px',
                      border: 'none',
                      backgroundColor: !draftMessage.trim() || isSubmitting ? '#c9c5bc' : '#3d403a',
                      color: 'white',
                      cursor: !draftMessage.trim() || isSubmitting ? 'not-allowed' : 'pointer',
                      fontWeight: 700,
                    }}
                  >
                    {isSubmitting ? <LoaderCircle size={16} className="spin" /> : <ArrowRight size={16} />}
                    ส่งคำถาม
                  </button>
                </div>
              </form>
            </div>
          </div>
        </section>

        <aside style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: '14px',
                  backgroundColor: 'rgba(196,164,112,0.16)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#8b6d3f',
                }}
              >
                <BrainCircuit size={20} />
              </div>
              <div>
                <h2 style={{ margin: 0, fontSize: '18px' }}>What Chat AI Is For</h2>
                <p style={{ margin: '4px 0 0', color: '#6b7280', fontSize: '13px' }}>
                  ใช้เพื่อ insight และ decision support
                </p>
              </div>
            </div>

            {STRATEGY_PILLARS.map((item) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.title}
                  style={{
                    padding: '16px',
                    borderRadius: '18px',
                    border: '1px solid #eee3d1',
                    backgroundColor: '#faf7f1',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Icon size={16} color="#8b6d3f" />
                    <span style={{ fontSize: '14px', fontWeight: 700 }}>{item.title}</span>
                  </div>
                  <p style={{ margin: 0, color: '#6b7280', fontSize: '13px', lineHeight: 1.6 }}>{item.description}</p>
                </div>
              );
            })}
          </div>

          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <FolderKanban size={18} color="#8b6d3f" />
              <h2 style={{ margin: 0, fontSize: '18px' }}>Current Scope</h2>
            </div>

            <div
              style={{
                padding: '16px',
                borderRadius: '18px',
                backgroundColor: selectedProject ? 'rgba(39,165,122,0.08)' : '#f3f4f6',
                border: `1px solid ${selectedProject ? 'rgba(39,165,122,0.18)' : '#e5e7eb'}`,
              }}
            >
              <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '6px' }}>
                {selectedProject ? 'Focused project' : 'Global analysis'}
              </div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#1f2937' }}>
                {selectedProject ? selectedProject.name : 'ทุกโครงการ'}
              </div>
            </div>

            {selectedProject ? (
              <Link
                to={`/project/detail/${selectedProject.project_id}`}
                state={{
                  projectId: selectedProject.project_id,
                  projectName: selectedProject.name,
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  width: 'fit-content',
                  textDecoration: 'none',
                  color: '#8b6d3f',
                  fontWeight: 700,
                  fontSize: '14px',
                }}
              >
                เปิดหน้าโครงการนี้
                <ArrowRight size={14} />
              </Link>
            ) : null}
          </div>
        </aside>
      </div>
    </div>
  );
}

export default ChatAIPage;
