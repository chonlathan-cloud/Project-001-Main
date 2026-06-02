import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Send, Paperclip, Mic, ChevronDown, FileText, Clock,
  Bot, ArrowUpRight
} from 'lucide-react';
import { Project, ApprovalRequest } from '../types';

interface ChatAIScreenProps {
  projects: Project[];
  approvals: ApprovalRequest[];
}

type MessageRole = 'assistant' | 'user';

interface SuggestedAction {
  icon: 'file' | 'clock';
  label: string;
  cta: string;
}

interface KpiCard {
  label: string;
  value: string;
  variant: 'normal' | 'danger';
}

interface ChatMessage {
  id: string;
  role: MessageRole;
  text: string;
  chips?: string[];
  kpiCards?: KpiCard[];
  bodyText?: string;
  suggestedActions?: SuggestedAction[];
}

// ── Initial conversation ───────────────────────────────────────────────
const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'msg-1',
    role: 'assistant',
    text: "Hello. I'm your Financial Assistant for Projects-001. How can I help you analyze the budget today?",
    chips: ['Show BOQ Summary', 'Analyze Cost Overruns', 'Pending Approvals'],
  },
  {
    id: 'msg-2',
    role: 'user',
    text: 'Can you summarize the current cost overruns for Phase 2: Framing?',
  },
  {
    id: 'msg-3',
    role: 'assistant',
    text: 'Certainly. Here is the current financial status for Phase 2: Framing.',
    kpiCards: [
      { label: 'Budgeted Cost',       value: '$145,000',          variant: 'normal' },
      { label: 'Actual Cost to Date', value: '$162,500',          variant: 'normal' },
      { label: 'Variance (Overrun)',   value: '+$17,500 (12%)',    variant: 'danger' },
    ],
    bodyText:
      'The primary driver for the overrun is an unexpected increase in lumber costs from Supplier B, and additional labor hours required due to weather delays.',
    suggestedActions: [
      { icon: 'file',  label: 'Review Change Order #42 (Lumber Price Adjustment)', cta: 'Review' },
      { icon: 'clock', label: 'Approve Overtime Labor Sheets for Week 14',          cta: 'View Sheets' },
    ],
  },
];

// ── Canned AI responses for demo ──────────────────────────────────────
function getAIResponse(input: string): ChatMessage {
  const q = input.toLowerCase();

  if (q.includes('boq') || q.includes('bill of quantities')) {
    return {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      text: 'Here is a summary of the current Bill of Quantities for Commercial Tower A.',
      kpiCards: [
        { label: 'Total BOQ Items',    value: '6 Line Items',  variant: 'normal' },
        { label: 'Synced Items',        value: '4 / 6',         variant: 'normal' },
        { label: 'Pending Sync',        value: '1 Modified',    variant: 'danger' },
      ],
      bodyText: 'The Double-Skin Curtain Wall item (08.4413) has been modified and requires re-sync with the Revit master model. Premium Terrazzo Flooring is marked as pending sync.',
      suggestedActions: [
        { icon: 'file',  label: 'Sync Curtain Wall BOQ with Revit', cta: 'Sync Now' },
        { icon: 'clock', label: 'Review Terrazzo Flooring Quantities', cta: 'Review' },
      ],
    };
  }

  if (q.includes('pending') || q.includes('approval')) {
    return {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      text: 'There are currently 3 pending approval requests awaiting your sign-off.',
      kpiCards: [
        { label: 'Pending Approvals', value: '3 Items',    variant: 'danger' },
        { label: 'Total Value',        value: '$81,000',   variant: 'normal' },
        { label: 'Oldest Request',     value: '10 days',   variant: 'normal' },
      ],
      bodyText:
        'The highest-priority item is the SCADA Cabinet Upgrade from Integratech Automation Ltd ($42,500). Two other change orders from Commercial Tower A are also pending structural and HVAC categories.',
      suggestedActions: [
        { icon: 'file',  label: 'Review SCADA Cabinet Upgrade (APP-104)', cta: 'Review' },
        { icon: 'clock', label: 'View All Pending Approvals Queue',        cta: 'Go to Queue' },
      ],
    };
  }

  if (q.includes('budget') || q.includes('spend') || q.includes('cost')) {
    return {
      id: `msg-${Date.now()}`,
      role: 'assistant',
      text: 'Here is an overview of the portfolio-level budget utilization.',
      kpiCards: [
        { label: 'Total Budget',   value: '$100.0M',  variant: 'normal' },
        { label: 'Total Spent',    value: '$75.1M',   variant: 'normal' },
        { label: 'Remaining',      value: '$24.9M',   variant: 'normal' },
      ],
      bodyText:
        'The Water Reclamation Facility (PRJ-004) is at 85% spend with $8.3M remaining. Commercial Tower A is at 45% with significant structural milestones upcoming.',
      suggestedActions: [
        { icon: 'file',  label: 'Export Full Portfolio Cost Report', cta: 'Export' },
        { icon: 'clock', label: 'View Cost Forecast in Data Warehouse', cta: 'View' },
      ],
    };
  }

  // Default fallback
  return {
    id: `msg-${Date.now()}`,
    role: 'assistant',
    text: `I've analyzed your query: "${input}". Based on current project data, here is what I found.`,
    bodyText:
      'I can help you with budget analysis, BOQ summaries, pending approvals, cost overruns, and financial forecasts. Try asking me something specific about a project or approval.',
    chips: ['Show BOQ Summary', 'Analyze Cost Overruns', 'Pending Approvals'],
  };
}

const PROJECT_SCOPE_OPTIONS = [
  'Optional Project Scope',
  'Commercial Tower A',
  'Residential Complex',
  'Logistics Hub',
  'Water Reclamation Facility',
];

// ── Component ─────────────────────────────────────────────────────────
export default function ChatAIScreen({ projects, approvals }: ChatAIScreenProps) {
  const [messages, setMessages]   = useState<ChatMessage[]>(INITIAL_MESSAGES);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping]   = useState(false);
  const [scope, setScope]         = useState('Optional Project Scope');
  const bottomRef                 = useRef<HTMLDivElement>(null);
  const inputRef                  = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const sendMessage = (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}-user`,
      role: 'user',
      text: trimmed,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsTyping(true);

    setTimeout(() => {
      const aiMsg = getAIResponse(trimmed);
      setIsTyping(false);
      setMessages((prev) => [...prev, aiMsg]);
    }, 1200);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputText);
    }
  };

  return (
    <div id="chat-ai-view" className="flex flex-col h-full bg-[#F5F4F1] overflow-hidden">

      {/* ── Top Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-6 py-3 bg-[#F5F4F1] border-b border-zinc-200 flex-shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="font-sans font-bold text-[17px] text-zinc-900 tracking-tight">
            Chat AI Financial Assistant
          </h1>
          {/* Project Scope Dropdown */}
          <div className="relative">
            <select
              id="chat-scope-selector"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              className="appearance-none pl-3 pr-7 py-1.5 text-[12px] font-sans font-medium text-zinc-600 bg-white border border-zinc-200 rounded-lg focus:outline-none cursor-pointer shadow-xs"
            >
              {PROJECT_SCOPE_OPTIONS.map((o) => <option key={o}>{o}</option>)}
            </select>
            <ChevronDown className="absolute right-2 top-2 h-3.5 w-3.5 text-zinc-400 pointer-events-none" />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button className="p-2 hover:bg-zinc-100 rounded-full transition-colors">
            <svg className="h-4 w-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6 6 0 10-12 0v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
          </button>
          <button className="p-2 hover:bg-zinc-100 rounded-full transition-colors">
            <svg className="h-4 w-4 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><circle cx="12" cy="12" r="10" strokeWidth={2}/><path strokeLinecap="round" strokeWidth={2} d="M12 8v4m0 4h.01"/></svg>
          </button>
          <div className="h-8 w-8 rounded-full bg-[#3F5E53] flex items-center justify-center text-white text-[10px] font-bold ml-1">JH</div>
        </div>
      </div>

      {/* ── Chat Messages ──────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        <AnimatePresence initial={false}>
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
            >
              {/* Avatar */}
              {msg.role === 'assistant' ? (
                <div className="h-9 w-9 rounded-full bg-[#3F5E53] flex items-center justify-center flex-shrink-0 shadow-sm mt-0.5">
                  <Bot className="h-4.5 w-4.5 text-white" />
                </div>
              ) : (
                <div className="h-9 w-9 rounded-full bg-zinc-700 flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm overflow-hidden">
                  <span className="text-white text-[10px] font-bold">JH</span>
                </div>
              )}

              {/* Bubble */}
              <div className={`max-w-[75%] ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-2`}>
                {msg.role === 'user' ? (
                  <div className="bg-white border border-zinc-200 rounded-2xl rounded-tr-sm px-4 py-3 shadow-xs">
                    <p className="font-sans text-[13px] text-zinc-800 leading-relaxed">{msg.text}</p>
                  </div>
                ) : (
                  <div className="bg-white border border-zinc-200 rounded-2xl rounded-tl-sm px-5 py-4 shadow-xs w-full">
                    {/* Main text */}
                    <p className="font-sans text-[13px] text-zinc-800 leading-relaxed mb-3">{msg.text}</p>

                    {/* Quick-action chips */}
                    {msg.chips && (
                      <div className="flex flex-wrap gap-2">
                        {msg.chips.map((chip) => (
                          <button
                            key={chip}
                            onClick={() => sendMessage(chip)}
                            className="px-3 py-1.5 rounded-full border border-zinc-200 bg-white hover:bg-zinc-50 text-[11px] font-sans font-medium text-zinc-700 transition-all"
                          >
                            {chip}
                          </button>
                        ))}
                      </div>
                    )}

                    {/* KPI cards */}
                    {msg.kpiCards && (
                      <div className="grid grid-cols-3 gap-3 mb-3">
                        {msg.kpiCards.map((kpi) => (
                          <div
                            key={kpi.label}
                            className={`rounded-xl p-3 border ${
                              kpi.variant === 'danger'
                                ? 'bg-red-50 border-red-200'
                                : 'bg-zinc-50 border-zinc-200'
                            }`}
                          >
                            <p className={`text-[10px] font-sans font-medium mb-1 ${
                              kpi.variant === 'danger' ? 'text-red-500' : 'text-zinc-500'
                            }`}>
                              {kpi.label}
                            </p>
                            <p className={`font-sans font-bold text-[16px] leading-tight ${
                              kpi.variant === 'danger' ? 'text-red-600' : 'text-zinc-900'
                            }`}>
                              {kpi.value}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Body text */}
                    {msg.bodyText && (
                      <p className="font-sans text-[12px] text-zinc-600 leading-relaxed mb-4">
                        {msg.bodyText}
                      </p>
                    )}

                    {/* Suggested next actions */}
                    {msg.suggestedActions && (
                      <div className="border-t border-zinc-100 pt-3 space-y-2">
                        <p className="text-[9px] font-bold font-sans text-zinc-400 uppercase tracking-widest mb-2">
                          Suggested Next Actions
                        </p>
                        {msg.suggestedActions.map((action) => (
                          <button
                            key={action.label}
                            className="w-full flex items-center justify-between px-3 py-2.5 border border-zinc-200 rounded-xl bg-white hover:bg-zinc-50 transition-all group"
                          >
                            <div className="flex items-center gap-2.5">
                              {action.icon === 'file' ? (
                                <FileText className="h-4 w-4 text-zinc-400 flex-shrink-0" />
                              ) : (
                                <Clock className="h-4 w-4 text-zinc-400 flex-shrink-0" />
                              )}
                              <span className="font-sans text-[12px] text-zinc-700 text-left leading-snug">
                                {action.label}
                              </span>
                            </div>
                            <span className="font-sans text-[11px] font-semibold text-[#3F5E53] group-hover:underline flex-shrink-0 ml-3">
                              {action.cta}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          ))}

          {/* Typing indicator */}
          {isTyping && (
            <motion.div
              key="typing"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex gap-3"
            >
              <div className="h-9 w-9 rounded-full bg-[#3F5E53] flex items-center justify-center flex-shrink-0 shadow-sm">
                <Bot className="h-4.5 w-4.5 text-white" />
              </div>
              <div className="bg-white border border-zinc-200 rounded-2xl rounded-tl-sm px-5 py-4 shadow-xs flex items-center gap-1.5">
                {[0, 1, 2].map((i) => (
                  <motion.span
                    key={i}
                    className="h-2 w-2 rounded-full bg-zinc-400 block"
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                  />
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      {/* ── Input Bar ──────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-6 pb-4 pt-3 border-t border-zinc-200 bg-[#F5F4F1]">
        <div className="flex items-center gap-2 bg-white border border-zinc-200 rounded-2xl shadow-xs px-4 py-3">
          <input
            id="chat-input-field"
            ref={inputRef}
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about project financials, budgets, or approvals..."
            className="flex-1 text-[13px] font-sans text-zinc-800 placeholder-zinc-400 bg-transparent focus:outline-none"
          />
          <button
            id="chat-send-btn"
            onClick={() => sendMessage(inputText)}
            disabled={!inputText.trim() || isTyping}
            className="h-8 w-8 rounded-xl bg-[#3F5E53] hover:bg-[#344E44] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-all flex-shrink-0"
          >
            <Send className="h-3.5 w-3.5 text-white" />
          </button>
        </div>

        {/* Footer actions + disclaimer */}
        <div className="flex items-center justify-between mt-2 px-1">
          <p className="font-sans text-[10px] text-zinc-400">
            AI can make mistakes. Verify critical financial data.
          </p>
          <div className="flex items-center gap-1">
            <button id="chat-attach-btn" className="p-1.5 hover:bg-zinc-100 rounded-lg transition-colors">
              <Paperclip className="h-3.5 w-3.5 text-zinc-400" />
            </button>
            <button id="chat-mic-btn" className="p-1.5 hover:bg-zinc-100 rounded-lg transition-colors">
              <Mic className="h-3.5 w-3.5 text-zinc-400" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
