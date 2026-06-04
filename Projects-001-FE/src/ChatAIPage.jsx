import { useCallback, useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import Loading from './components/Loading';
import {
  ChatAIHero,
  ChatAISidePanel,
  ChatComposer,
  ChatContextBar,
  ChatEmptyState,
  ChatLoadingMessage,
  ChatMessage,
  ChatNotice,
} from './components/ChatAIWorkspace';
import { askChatQuestion, clearChatHistory, getChatHistory, getInputProjectOptions } from './api';

const SUGGESTED_PROMPTS = [
  {
    kind: 'budget',
    title: 'Budget Risk',
    description: 'หาโครงการหรืองานที่มีแนวโน้มใช้งบเกิน',
    prompt: 'สรุปความเสี่ยงงบบานปลายจากข้อมูลที่มีอยู่ พร้อมบอกประเด็นที่ควรตรวจต่อ',
  },
  {
    kind: 'cash',
    title: 'Cash Flow',
    description: 'มองภาพรวมรายรับรายจ่ายและคิวอนุมัติ',
    prompt: 'สรุปภาพรวม cash flow ปัจจุบัน และระบุจุดที่กระทบสภาพคล่องมากที่สุด',
  },
  {
    kind: 'overdue',
    title: 'Overdue',
    description: 'เน้นหายอดค้างและงานที่ควรถูกเร่งรัด',
    prompt: 'มีรายการ overdue หรือคิวที่ควรเร่งจัดการอะไรบ้าง',
  },
  {
    kind: 'compare',
    title: 'Material vs Labor',
    description: 'เปรียบเทียบต้นทุนวัสดุกับค่าแรง',
    prompt: 'เปรียบเทียบค่าแรงกับค่าวัสดุจากข้อมูลล่าสุด และชี้รายการที่ผิดปกติ',
  },
];

const DATA_SIGNALS = [
  {
    kind: 'boq',
    title: 'BOQ + Cost Plan',
    description: 'งบประมาณ รายการงาน และต้นทุนตั้งต้น',
  },
  {
    kind: 'transactions',
    title: 'Transactions',
    description: 'เงินเข้า เงินออก และหลักฐานประกอบ',
  },
  {
    kind: 'approvals',
    title: 'Approval Queue',
    description: 'รายการรออนุมัติ ยอดค้าง และสถานะงาน',
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

  const submitQuestion = useCallback(
    async (rawMessage) => {
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
    },
    [isSubmitting, projectId, selectedProject?.name]
  );

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
  }, [isSubmitting, loading, routeAutoSubmit, routeInitialPrompt, submitQuestion]);

  if (loading) return <Loading />;

  return (
    <div className="chat-ai-page">
      <ChatAIHero
        selectedProject={selectedProject}
        messageCount={messages.length}
        routeContextLabel={routeContextLabel}
        routeInitialPrompt={routeInitialPrompt}
      />

      {pageError ? <ChatNotice tone="error">{pageError}</ChatNotice> : null}

      <div className="chat-ai-layout">
        <section className="chat-ai-conversation-panel">
          <ChatContextBar
            projects={projects}
            projectId={projectId}
            onProjectChange={setProjectId}
            selectedProject={selectedProject}
            onClearConversation={clearConversation}
            isClearingHistory={isClearingHistory}
            canClear={messages.length > 0 || Boolean(composerError)}
          />

          <div className="chat-ai-thread-shell">
            <div className="chat-ai-thread">
              {messages.length === 0 ? (
                <ChatEmptyState
                  prompts={SUGGESTED_PROMPTS}
                  onPromptClick={handlePromptClick}
                  disabled={isSubmitting}
                />
              ) : (
                <>
                  {messages.map((message) => (
                    <ChatMessage key={message.id} message={message} />
                  ))}

                  {isSubmitting ? <ChatLoadingMessage /> : null}

                  <div ref={messagesEndRef} />
                </>
              )}
            </div>
          </div>

          <ChatComposer
            draftMessage={draftMessage}
            onDraftMessageChange={setDraftMessage}
            onSubmit={handleComposerSubmit}
            isSubmitting={isSubmitting}
            composerError={composerError}
            selectedProject={selectedProject}
          />
        </section>

        <ChatAISidePanel
          prompts={SUGGESTED_PROMPTS}
          dataSignals={DATA_SIGNALS}
          selectedProject={selectedProject}
          onPromptClick={handlePromptClick}
          isSubmitting={isSubmitting}
        />
      </div>
    </div>
  );
}

export default ChatAIPage;
