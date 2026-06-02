import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Search, Bell, HelpCircle, ZoomIn, ZoomOut,
  FileText, MoreVertical, ScanLine,
  CheckCircle2, XCircle, CreditCard, ThumbsUp
} from 'lucide-react';
import { ApprovalRequest } from '../types';

interface ApprovalsScreenProps {
  approvals: ApprovalRequest[];
  handleApprove: (id: string) => void;
  handleReject: (id: string) => void;
}

interface LineItem {
  description: string;
  qty: number;
  price: number;
}

const INVOICE_DATA: Record<string, {
  vendorName: string;
  invoiceNumber: string;
  date: string;
  totalAmount: number;
  submittedVia: string;
  lineItems: LineItem[];
}> = {
  'APP-101': {
    vendorName: 'Acme Construction Materials',
    invoiceNumber: 'INV-2023-041',
    date: '24/10/2023',
    totalAmount: 4520.00,
    submittedVia: 'System via OCR',
    lineItems: [
      { description: 'Portland Cement (50lb)', qty: 100, price: 15.00 },
      { description: 'Rebar #4 (20ft)', qty: 250, price: 12.08 },
    ],
  },
  'APP-102': {
    vendorName: 'BreezeAir Thermal Solutions',
    invoiceNumber: 'INV-2023-102',
    date: '20/10/2023',
    totalAmount: 14500.00,
    submittedVia: 'Email Attachment',
    lineItems: [
      { description: 'Elastomeric Foam Jacket (10m)', qty: 80, price: 95.00 },
      { description: 'Low-E Duct Wrap Install', qty: 50, price: 125.00 },
    ],
  },
  'APP-103': {
    vendorName: 'TerraFirm Earthworkers',
    invoiceNumber: 'INV-2023-088',
    date: '18/10/2023',
    totalAmount: 8700.00,
    submittedVia: 'Portal Upload',
    lineItems: [
      { description: 'Geotextile Silt Fence (50m)', qty: 12, price: 300.00 },
      { description: 'Silt Barrier Installation', qty: 30, price: 150.00 },
    ],
  },
  'APP-104': {
    vendorName: 'Integratech Automation Ltd',
    invoiceNumber: 'INV-2023-211',
    date: '15/10/2023',
    totalAmount: 42500.00,
    submittedVia: 'System via OCR',
    lineItems: [
      { description: 'SCADA Control Cabinet', qty: 5, price: 6000.00 },
      { description: 'Trip Circuit Integration', qty: 25, price: 500.00 },
    ],
  },
  'APP-105': {
    vendorName: 'Apex Builders Co.',
    invoiceNumber: 'INV-2023-055',
    date: '10/10/2023',
    totalAmount: 115000.00,
    submittedVia: 'Email Attachment',
    lineItems: [
      { description: 'Acoustic Glazing Panels (m2)', qty: 500, price: 180.00 },
      { description: 'Facade System Installation', qty: 200, price: 200.00 },
    ],
  },
};

const TIME_LABELS: Record<string, string> = {
  'APP-101': 'Today, 10:45 AM',
  'APP-102': 'Yesterday, 3:20 PM',
  'APP-103': 'May 22, 4:32 PM',
  'APP-104': 'May 20, 9:15 AM',
  'APP-105': 'May 15, 2:00 PM',
};

export default function ApprovalsScreen({ approvals, handleApprove, handleReject }: ApprovalsScreenProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(
    approvals.find((a) => a.status === 'pending')?.id ?? approvals[0]?.id ?? null
  );
  const [zoomLevel, setZoomLevel] = useState(1);

  const pendingCount = approvals.filter((a) => a.status === 'pending').length;

  const filtered = approvals.filter((req) => {
    const q = searchQuery.toLowerCase();
    return (
      req.title.toLowerCase().includes(q) ||
      req.subcontractor.toLowerCase().includes(q) ||
      req.id.toLowerCase().includes(q) ||
      req.projectName.toLowerCase().includes(q)
    );
  });

  const selected = approvals.find((a) => a.id === selectedId) ?? null;
  const inv = selectedId ? INVOICE_DATA[selectedId] : null;

  return (
    /* Root: fills h-full provided by parent flex container */
    <div id="approvals-view" className="flex flex-col h-full bg-[#F5F4F1] overflow-hidden">

      {/* ── Top Header Bar ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-6 py-3 bg-[#F5F4F1] border-b border-zinc-200 flex-shrink-0">
        {/* Search */}
        <div className="relative w-56">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-400" />
          <input
            id="approvals-search-field"
            type="text"
            placeholder="Search approvals..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-2 text-[11px] font-sans rounded-lg border border-zinc-200 bg-white focus:outline-none focus:border-zinc-300 transition-all placeholder-zinc-400 shadow-xs"
          />
        </div>

        {/* Right icons */}
        <div className="flex items-center gap-2">
          <button id="approvals-bell-btn" className="p-2 hover:bg-zinc-100 rounded-full transition-colors">
            <Bell className="h-4 w-4 text-zinc-500" />
          </button>
          <button id="approvals-help-btn" className="p-2 hover:bg-zinc-100 rounded-full transition-colors">
            <HelpCircle className="h-4 w-4 text-zinc-500" />
          </button>
          <div className="h-8 w-8 rounded-full bg-[#3F5E53] flex items-center justify-center text-white text-[10px] font-bold ml-1">
            JH
          </div>
        </div>
      </div>

      {/* ── Main Body: two-panel row ────────────────────────────────────────── */}
      <div className="flex flex-1 gap-4 p-4 overflow-hidden">

        {/* ── LEFT CARD: Review Queue ─────────────────────────── */}
        <div className="w-[240px] min-w-[200px] flex flex-col bg-white rounded-2xl border border-zinc-200 shadow-xs overflow-hidden flex-shrink-0">
          {/* Title */}
          <div className="px-4 pt-4 pb-3 flex-shrink-0">
            <h2 className="font-sans font-bold text-[16px] text-zinc-900 tracking-tight">Review Queue</h2>
            <p className="text-[11px] text-zinc-400 font-sans mt-0.5">
              {pendingCount} Pending Item{pendingCount !== 1 ? 's' : ''}
            </p>
          </div>

          {/* Scrollable list */}
          <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-2">
            {filtered.length === 0 ? (
              <div className="py-8 text-center">
                <p className="text-[11px] text-zinc-400 font-sans">No items match your search.</p>
              </div>
            ) : (
              filtered.map((req) => {
                const isSelected = req.id === selectedId;
                const invData = INVOICE_DATA[req.id];
                return (
                  <div
                    key={req.id}
                    id={`queue-item-${req.id}`}
                    onClick={() => setSelectedId(req.id)}
                    className={`p-3 rounded-xl cursor-pointer transition-all border ${
                      isSelected
                        ? 'bg-white border-zinc-200 shadow-sm'
                        : 'border-transparent hover:bg-zinc-50'
                    }`}
                  >
                    {/* Status + time */}
                    <div className="flex items-center justify-between mb-1.5">
                      <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded font-mono ${
                        req.status === 'pending'   ? 'bg-amber-100 text-amber-700' :
                        req.status === 'approved'  ? 'bg-emerald-100 text-emerald-700' :
                                                     'bg-red-100 text-red-700'
                      }`}>
                        {req.status === 'pending' ? 'Pending' : req.status === 'approved' ? 'Approved' : 'Rejected'}
                      </span>
                      <span className="text-[9px] text-zinc-400 font-sans">{TIME_LABELS[req.id] ?? req.date}</span>
                    </div>
                    {/* Invoice name */}
                    <h3 className="font-sans font-bold text-[12px] text-zinc-900 leading-snug mb-0.5 line-clamp-2">
                      {invData ? `Invoice #${invData.invoiceNumber}` : req.title}
                    </h3>
                    {/* Vendor */}
                    <p className="text-[11px] text-zinc-500 font-sans truncate mb-2">
                      {invData?.vendorName ?? req.subcontractor}
                    </p>
                    {/* Amount */}
                    <div className="flex items-center justify-between">
                      <span className="font-sans font-bold text-[13px] text-zinc-900">
                        ${(invData?.totalAmount ?? req.amount).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </span>
                      <FileText className="h-4 w-4 text-zinc-300" />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* ── RIGHT CARD: Invoice Detail ──────────────────────── */}
        {selected && inv ? (
          <AnimatePresence mode="wait">
            <motion.div
              key={selected.id}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.15 }}
              className="flex-1 flex flex-col bg-white rounded-2xl border border-zinc-200 shadow-xs overflow-hidden"
            >
              {/* Card top header */}
              <div className="flex items-start justify-between px-5 py-4 border-b border-zinc-100 flex-shrink-0">
                <div>
                  <h1 className="font-sans font-bold text-[18px] text-zinc-900 tracking-tight">
                    Invoice #{inv.invoiceNumber}
                  </h1>
                  <p className="text-[11px] text-zinc-500 font-sans mt-0.5">
                    Submitted by {inv.submittedVia}
                  </p>
                </div>
                <button className="p-1.5 hover:bg-zinc-100 rounded-lg transition-colors mt-0.5">
                  <MoreVertical className="h-4 w-4 text-zinc-400" />
                </button>
              </div>

              {/* Two-column body: Extracted Data + Original Document */}
              <div className="flex flex-1 overflow-hidden divide-x divide-zinc-100">

                {/* Extracted Data */}
                <div className="flex-1 overflow-y-auto p-5 space-y-4">
                  <div className="flex items-center gap-2 mb-1">
                    <ScanLine className="h-4 w-4 text-zinc-500" />
                    <span className="font-sans font-bold text-[13px] text-zinc-800">Extracted Data</span>
                  </div>

                  {/* Vendor Name */}
                  <div className="space-y-1">
                    <label className="text-[11px] font-sans font-semibold text-zinc-600">Vendor Name</label>
                    <input
                      readOnly
                      value={inv.vendorName}
                      className="w-full px-3 py-2 text-[12px] font-sans text-zinc-800 bg-white border border-zinc-200 rounded-lg focus:outline-none"
                    />
                  </div>

                  {/* Invoice Number + Date */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-[11px] font-sans font-semibold text-zinc-600">Invoice Number</label>
                      <input
                        readOnly
                        value="INV-2023-"
                        className="w-full px-3 py-2 text-[12px] font-sans text-zinc-800 bg-white border border-zinc-200 rounded-lg focus:outline-none"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[11px] font-sans font-semibold text-zinc-600">Date</label>
                      <input
                        readOnly
                        value={inv.date}
                        className="w-full px-3 py-2 text-[12px] font-sans text-zinc-800 bg-white border border-zinc-200 rounded-lg focus:outline-none"
                      />
                    </div>
                  </div>

                  {/* Total Amount */}
                  <div className="space-y-1">
                    <label className="text-[11px] font-sans font-semibold text-zinc-600">Total Amount</label>
                    <div className="flex items-center border border-zinc-200 rounded-lg overflow-hidden">
                      <span className="px-3 py-2 text-[12px] font-sans text-zinc-500 bg-zinc-50 border-r border-zinc-200 flex-shrink-0">$</span>
                      <input
                        readOnly
                        value={inv.totalAmount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                        className="flex-1 px-3 py-2 text-[12px] font-sans text-zinc-800 bg-white focus:outline-none min-w-0"
                      />
                    </div>
                  </div>

                  {/* Line Items */}
                  <div className="space-y-1">
                    <label className="text-[11px] font-sans font-semibold text-zinc-600">Line Items</label>
                    <div className="border border-zinc-200 rounded-xl overflow-hidden">
                      <div className="grid grid-cols-[1fr_56px_72px] bg-zinc-50 px-4 py-2.5 border-b border-zinc-200">
                        <span className="text-[10px] font-bold font-sans text-zinc-500 uppercase tracking-wide">Description</span>
                        <span className="text-[10px] font-bold font-sans text-zinc-500 uppercase tracking-wide text-center">Qty</span>
                        <span className="text-[10px] font-bold font-sans text-zinc-500 uppercase tracking-wide text-right">Price</span>
                      </div>
                      {inv.lineItems.map((item, i) => (
                        <div
                          key={i}
                          className={`grid grid-cols-[1fr_56px_72px] px-4 py-3 ${i < inv.lineItems.length - 1 ? 'border-b border-zinc-100' : ''}`}
                        >
                          <span className="text-[12px] font-sans text-zinc-800 leading-snug">{item.description}</span>
                          <span className="text-[12px] font-sans text-zinc-700 text-center self-center">{item.qty}</span>
                          <span className="text-[12px] font-sans text-zinc-700 text-right self-center">${item.price.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Original Document */}
                <div className="w-[240px] flex-shrink-0 flex flex-col overflow-hidden">
                  {/* Header */}
                  <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-100 flex-shrink-0">
                    <span className="text-[10px] font-bold font-sans text-zinc-400 uppercase tracking-widest">Original Document</span>
                    <div className="flex items-center gap-0.5">
                      <button
                        id="zoom-in-btn"
                        onClick={() => setZoomLevel((z) => Math.min(z + 0.1, 1.5))}
                        className="p-1.5 hover:bg-zinc-100 rounded-lg transition-colors"
                      >
                        <ZoomIn className="h-3 w-3 text-zinc-500" />
                      </button>
                      <button
                        id="zoom-out-btn"
                        onClick={() => setZoomLevel((z) => Math.max(z - 0.1, 0.6))}
                        className="p-1.5 hover:bg-zinc-100 rounded-lg transition-colors"
                      >
                        <ZoomOut className="h-3 w-3 text-zinc-500" />
                      </button>
                    </div>
                  </div>

                  {/* Document paper mock */}
                  <div className="flex-1 overflow-hidden p-4">
                    <div className="h-full bg-white border border-zinc-200 rounded-xl overflow-hidden shadow-xs flex flex-col">
                      <div
                        style={{ transform: `scale(${zoomLevel})`, transformOrigin: 'top center', transition: 'transform 0.2s ease' }}
                        className="p-5 flex-1"
                      >
                        {/* Doc header */}
                        <div className="text-center mb-5 pb-3 border-b border-zinc-200">
                          <h3 className="font-sans font-extrabold text-[13px] text-zinc-900 uppercase tracking-wide">
                            {inv.vendorName.split(' ').slice(0, 2).join(' ').toUpperCase()}
                          </h3>
                          <p className="text-[9px] text-zinc-500 font-sans mt-0.5">Invoice: {inv.invoiceNumber}</p>
                        </div>

                        {/* Line items in doc */}
                        <div className="space-y-2 mb-5">
                          {inv.lineItems.map((item, i) => (
                            <div key={i} className="flex items-start justify-between gap-2 text-[9px] font-sans">
                              <span className="text-zinc-700 leading-snug">{item.description}</span>
                              <span className="font-bold text-zinc-900 flex-shrink-0">
                                ${(item.qty * item.price).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                              </span>
                            </div>
                          ))}
                        </div>

                        {/* Total */}
                        <div className="pt-3 border-t border-zinc-200 flex items-center justify-between">
                          <span className="font-sans font-extrabold text-[10px] text-zinc-900 uppercase tracking-wide">Total</span>
                          <span className="font-sans font-extrabold text-[12px] text-zinc-900">
                            ${inv.totalAmount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Action Footer ── */}
              <div className="flex items-center gap-3 px-5 py-3.5 border-t border-zinc-100 bg-zinc-50/60 flex-shrink-0">
                <button
                  id="add-note-btn"
                  className="text-[11px] font-sans text-zinc-400 hover:text-zinc-700 transition-colors"
                >
                  Add approval/rejection
                </button>
                <div className="flex-1" />

                {selected.status === 'pending' ? (
                  <>
                    <button
                      id="action-reject-btn"
                      onClick={() => handleReject(selected.id)}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-zinc-200 bg-white hover:bg-red-50 hover:border-red-200 text-zinc-700 hover:text-red-700 font-sans font-semibold text-[12px] transition-all"
                    >
                      <XCircle className="h-3.5 w-3.5" />
                      Reject
                    </button>
                    <button
                      id="action-mark-paid-btn"
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg border border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-700 font-sans font-semibold text-[12px] transition-all"
                    >
                      <CreditCard className="h-3.5 w-3.5" />
                      Mark as Paid
                    </button>
                    <button
                      id="action-approve-btn"
                      onClick={() => handleApprove(selected.id)}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#3F5E53] hover:bg-[#344E44] text-white font-sans font-semibold text-[12px] transition-all shadow-sm"
                    >
                      <ThumbsUp className="h-3.5 w-3.5" />
                      Approve
                    </button>
                  </>
                ) : (
                  <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-bold font-sans ${
                    selected.status === 'approved'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-red-50 text-red-700 border border-red-200'
                  }`}>
                    {selected.status === 'approved'
                      ? <><CheckCircle2 className="h-3.5 w-3.5" /> Approved</>
                      : <><XCircle className="h-3.5 w-3.5" /> Rejected</>}
                  </span>
                )}
              </div>
            </motion.div>
          </AnimatePresence>
        ) : (
          <div className="flex-1 flex items-center justify-center bg-white rounded-2xl border border-zinc-200">
            <div className="text-center space-y-2">
              <FileText className="h-12 w-12 text-zinc-200 mx-auto" />
              <p className="font-sans text-sm font-semibold text-zinc-400">Select an item from the queue</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
