import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Check, X, Search, Clock, FileCheck, FileX, Paperclip, User, Calendar, MapPin, SlidersHorizontal } from 'lucide-react';
import { ApprovalRequest } from '../types';

interface ApprovalsScreenProps {
  approvals: ApprovalRequest[];
  handleApprove: (id: string) => void;
  handleReject: (id: string) => void;
}

export default function ApprovalsScreen({ approvals, handleApprove, handleReject }: ApprovalsScreenProps) {
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectionInput, setShowRejectionInput] = useState(false);

  // Filter & Search Logic
  const filteredRequests = approvals.filter((req) => {
    const matchesFilter = filter === 'all' || req.status === filter;
    const matchesSearch =
      req.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      req.projectName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      req.subcontractor.toLowerCase().includes(searchQuery.toLowerCase()) ||
      req.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const getStatusBadge = (status: ApprovalRequest['status']) => {
    switch (status) {
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wide font-semibold text-amber-600 bg-amber-50 px-2.5 py-1 rounded-full border border-amber-100">
            <Clock className="h-3 w-3" />
            Pending Sign-off
          </span>
        );
      case 'approved':
        return (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wide font-semibold text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100">
            <FileCheck className="h-3 w-3" />
            Approved
          </span>
        );
      case 'rejected':
        return (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wide font-semibold text-red-600 bg-red-50 px-2.5 py-1 rounded-full border border-red-100">
            <FileX className="h-3 w-3" />
            Rejected
          </span>
        );
    }
  };

  const executeApprovalAction = (action: 'approve' | 'reject') => {
    if (!selectedRequest) return;
    if (action === 'approve') {
      handleApprove(selectedRequest.id);
      setSelectedRequest(null);
    } else {
      if (!showRejectionInput) {
        setShowRejectionInput(true);
      } else {
        handleReject(selectedRequest.id);
        setShowRejectionInput(false);
        setRejectionReason('');
        setSelectedRequest(null);
      }
    }
  };

  return (
    <div id="approvals-view" className="space-y-8">
      {/* Upper Title Section */}
      <div>
        <h2 className="font-sans font-bold text-3xl text-zinc-900 tracking-tight">Contractual Approvals</h2>
        <p className="font-mono text-xs text-zinc-500 mt-1">Review, authorize, or dismiss Program change orders & design modifications</p>
      </div>

      {/* Control Filters Bar */}
      <div className="flex flex-col md:flex-row justify-between items-stretch md:items-center gap-4 bg-white p-3 border border-zinc-200 rounded-2xl shadow-2xs">
        {/* Left Status Tabs */}
        <div className="flex items-center gap-1 bg-zinc-100 p-1 rounded-xl">
          {[
            { id: 'all', label: 'All Logged' },
            { id: 'pending', label: 'Pending Gate' },
            { id: 'approved', label: 'Approved' },
            { id: 'rejected', label: 'Rejected' },
          ].map((tab) => (
            <button
              id={`tab-filter-${tab.id}`}
              key={tab.id}
              onClick={() => setFilter(tab.id as any)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-medium font-sans transition-all duration-150 ${
                filter === tab.id
                  ? 'bg-white text-zinc-950 shadow-xs'
                  : 'text-zinc-500 hover:text-zinc-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Right Search Bar */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-zinc-400" />
          <input
            id="approvals-search-field"
            type="text"
            placeholder="Search change-orders, subcontractors, or programs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-xs font-sans rounded-xl border border-zinc-200 bg-zinc-50 hover:border-zinc-300 focus:outline-none focus:border-zinc-400 focus:bg-white transition-all shadow-2xs"
          />
        </div>
      </div>

      {/* Approvals Table/List layout */}
      <div id="approvals-list-panel" className="bg-white border border-zinc-200 rounded-2xl overflow-hidden shadow-2xs">
        {filteredRequests.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <span className="font-mono text-[10px] text-zinc-400 uppercase font-semibold">Empty State</span>
            <p className="font-sans text-xs text-zinc-500">No approval submittals matched your filter inputs.</p>
          </div>
        ) : (
          <div className="divide-y divide-zinc-100">
            {filteredRequests.map((req) => (
              <div
                id={`approval-row-${req.id}`}
                key={req.id}
                onClick={() => {
                  setSelectedRequest(req);
                  setShowRejectionInput(false);
                  setRejectionReason('');
                }}
                className="p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 hover:bg-zinc-50/50 cursor-pointer transition-colors"
              >
                {/* Meta Header */}
                <div className="flex-1 min-w-0 space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-mono text-[9px] font-semibold tracking-wider text-zinc-400 uppercase bg-zinc-100 px-1.5 py-0.5 rounded">
                      {req.id}
                    </span>
                    <span className="font-sans font-medium text-xs text-zinc-500 truncate max-w-[180px]">
                      {req.projectName}
                    </span>
                    <span className="text-zinc-300">•</span>
                    <span className="font-mono text-[10px] text-zinc-400">{req.date}</span>
                  </div>
                  <h3 className="font-sans font-bold text-sm text-zinc-900 tracking-tight leading-none">
                    {req.title}
                  </h3>
                  <p className="font-sans text-xs text-zinc-500 truncate max-w-[480px]">
                    Contractor: <strong className="font-medium text-zinc-750">{req.subcontractor}</strong>
                  </p>
                </div>

                {/* Amount / Action State */}
                <div className="flex items-center gap-6 self-stretch md:self-auto justify-between border-t md:border-t-0 border-zinc-100 pt-3 md:pt-0">
                  <div className="text-left md:text-right space-y-0.5">
                    <span className="font-mono text-[9px] uppercase tracking-wider text-zinc-400 block font-semibold">Change Cost</span>
                    <span className="font-sans font-bold text-sm text-zinc-900">
                      ${req.amount.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    {getStatusBadge(req.status)}
                    <span className="text-xs text-zinc-300 hover:text-zinc-500 font-mono font-medium">Review &gt;</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* HIGH FIDELITY ACTION MODAL DRAWING SECTION */}
      <AnimatePresence>
        {selectedRequest && (
          <div id="approval-detail-modal" className="fixed inset-0 bg-zinc-900/50 flex justify-center items-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-xl bg-white rounded-3xl overflow-hidden border border-zinc-200 shadow-2xl flex flex-col max-h-[90vh]"
            >
              {/* Headings */}
              <div className="p-6 border-b border-zinc-200 bg-zinc-50 flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10px] font-semibold tracking-wider text-zinc-400 uppercase bg-zinc-200 px-1.5 py-0.5 rounded">
                      {selectedRequest.id}
                    </span>
                    <span className="font-mono text-[10px] uppercase font-semibold text-zinc-500">
                      {selectedRequest.category} Group
                    </span>
                  </div>
                  <h3 className="font-sans font-bold text-lg text-zinc-900 mt-2 tracking-tight">
                    {selectedRequest.title}
                  </h3>
                  <p className="font-mono text-xs text-zinc-500 mt-0.5">{selectedRequest.projectName}</p>
                </div>
                <button
                  id="close-approval-modal-top"
                  onClick={() => setSelectedRequest(null)}
                  className="p-1.5 hover:bg-zinc-200 rounded-lg text-zinc-400 hover:text-zinc-700 transition-all font-mono text-xs font-semibold"
                >
                  ESC ✕
                </button>
              </div>

              {/* Central Information Body */}
              <div className="p-6 overflow-y-auto space-y-6 flex-1">
                {/* Meta details */}
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div className="p-3.5 bg-zinc-50 border border-zinc-150 rounded-xl space-y-1">
                    <span className="font-mono text-[9px] uppercase tracking-wider text-zinc-450 font-semibold block">Requested By</span>
                    <div className="flex items-center gap-1.5 font-medium text-zinc-800">
                      <User className="h-3.5 w-3.5 text-zinc-400" />
                      <span>{selectedRequest.requestedBy}</span>
                    </div>
                  </div>
                  <div className="p-3.5 bg-zinc-50 border border-zinc-150 rounded-xl space-y-1">
                    <span className="font-mono text-[9px] uppercase tracking-wider text-zinc-450 font-semibold block">Original Date</span>
                    <div className="flex items-center gap-1.5 font-mono text-zinc-700">
                      <Calendar className="h-3.5 w-3.5 text-zinc-400" />
                      <span>{selectedRequest.date}</span>
                    </div>
                  </div>
                  <div className="p-3.5 bg-zinc-50 border border-zinc-150 rounded-xl space-y-1">
                    <span className="font-mono text-[9px] uppercase tracking-wider text-zinc-450 font-semibold block">Subcontractor</span>
                    <div className="flex items-center gap-1.5 font-medium text-zinc-800">
                      <MapPin className="h-3.5 w-3.5 text-zinc-400" />
                      <span>{selectedRequest.subcontractor}</span>
                    </div>
                  </div>
                  <div className="p-3.5 bg-zinc-50 border border-zinc-150 rounded-xl space-y-1">
                    <span className="font-mono text-[9px] uppercase tracking-wider text-zinc-450 font-semibold block">Financial Impact</span>
                    <span className="font-sans font-bold text-sm text-zinc-950">
                      ${selectedRequest.amount.toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* Submittal Narrative */}
                <div className="space-y-2">
                  <span className="font-mono text-[9px] uppercase tracking-wider text-zinc-450 font-semibold block">Change Narrative & Scope justifications</span>
                  <p className="font-sans text-xs text-zinc-650 leading-relaxed bg-zinc-50 p-4 border border-zinc-150 rounded-2xl">
                    {selectedRequest.description}
                  </p>
                </div>

                {/* Attachments Section */}
                <div className="space-y-2">
                  <span className="font-mono text-[9px] uppercase tracking-wider text-zinc-450 font-semibold block">Verify Documents</span>
                  <div className="flex gap-2">
                    <div className="flex-1 p-2.5 bg-white border border-zinc-200 rounded-xl flex items-center justify-between text-xs font-sans text-zinc-600">
                      <div className="flex items-center gap-2">
                        <Paperclip className="h-3.5 w-3.5 text-zinc-400" />
                        <span className="font-medium truncate max-w-[140px]">revit_export_steel_detail.pdf</span>
                      </div>
                      <span className="font-mono text-[9px] text-zinc-400 uppercase font-semibold">4.8 MB</span>
                    </div>
                    <div className="flex-1 p-2.5 bg-white border border-zinc-200 rounded-xl flex items-center justify-between text-xs font-sans text-zinc-600">
                      <div className="flex items-center gap-2">
                        <Paperclip className="h-3.5 w-3.5 text-zinc-400" />
                        <span className="font-medium truncate max-w-[140px]">cost_ledger_materials_inc.xlsx</span>
                      </div>
                      <span className="font-mono text-[9px] text-zinc-400 uppercase font-semibold">1.2 MB</span>
                    </div>
                  </div>
                </div>

                {/* Rejection input area */}
                {showRejectionInput && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="p-4 bg-red-50/50 border border-red-200 rounded-xl space-y-2 overflow-hidden"
                  >
                    <label className="font-sans text-xs font-semibold text-red-700 block">Provide governance dismissal reason:</label>
                    <textarea
                      id="rejection-reason-textarea"
                      placeholder="Specify material issues, missing certifications, or budget limitations..."
                      value={rejectionReason}
                      onChange={(e) => setRejectionReason(e.target.value)}
                      className="w-full text-xs font-sans p-2.5 border border-red-200 rounded-lg focus:outline-none focus:border-red-400 bg-white"
                      rows={3}
                    />
                  </motion.div>
                )}
              </div>

              {/* Action Buttons Footer */}
              <div className="p-6 border-t border-zinc-200 bg-zinc-50 flex gap-3">
                {selectedRequest.status === 'pending' ? (
                  <>
                    <button
                      id="modal-reject-action-btn"
                      onClick={() => executeApprovalAction('reject')}
                      className="flex-1 py-2.5 border border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-700 font-semibold rounded-xl text-xs transition-colors"
                    >
                      {showRejectionInput ? 'Confirm Reject' : 'Reject Change Order'}
                    </button>
                    <button
                      id="modal-approve-action-btn"
                      onClick={() => executeApprovalAction('approve')}
                      className="flex-1 py-2.5 bg-zinc-900 text-white hover:bg-zinc-800 font-semibold rounded-xl text-xs flex items-center justify-center gap-1.5 transition-colors shadow-sm"
                    >
                      <Check className="h-4 w-4" />
                      <span>Approve Code Change</span>
                    </button>
                  </>
                ) : (
                  <button
                    id="modal-dismiss-btn"
                    onClick={() => setSelectedRequest(null)}
                    className="w-full py-2.5 bg-zinc-900 text-white hover:bg-zinc-800 font-semibold rounded-xl text-xs transition-colors text-center"
                  >
                    Close Log View
                  </button>
                )}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
