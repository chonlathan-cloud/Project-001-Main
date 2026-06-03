import { useState } from 'react';
import { motion } from 'motion/react';
import {
  Search, Bell, HelpCircle, Download,
  ChevronDown, Calendar, ChevronLeft, ChevronRight
} from 'lucide-react';
import { Project } from '../types';

interface InsightsScreenProps {
  projects: Project[];
}

type RecordStatus = 'CLEARED' | 'PENDING' | 'DISPUTED';
type RecordType = 'Material' | 'Equipment' | 'Labor' | 'Admin' | 'Subcontract';

interface FinancialRecord {
  id: string;
  date: string;
  projectRef: string;
  description: string;
  type: RecordType;
  status: RecordStatus;
  amount: number;
  balance: number;
}

const ALL_RECORDS: FinancialRecord[] = [
  { id: '#INV-2023-0891', date: '2023-10-24', projectRef: 'PRJ-A', description: 'Structural Steel Delivery & Installation Works Q4', type: 'Material',    status: 'CLEARED',  amount: 124500.00, balance: 875500.00 },
  { id: '#PO-2023-442',   date: '2023-10-22', projectRef: 'PRJ-B', description: 'Site Prep Equipment Rental — Excavator & Bulldozer', type: 'Equipment',   status: 'PENDING',  amount: 18250.50,  balance: 1204000.00 },
  { id: '#INV-2023-0892', date: '2023-10-21', projectRef: 'PRJ-A', description: 'Subcontractor: Electrical Rough-In Package Phase 2', type: 'Labor',       status: 'CLEARED',  amount: 45000.00,  balance: 920500.00 },
  { id: '#FEE-2023-011',  date: '2023-10-18', projectRef: 'PRJ-C', description: 'Municipal Permit Fees — Building & Fire Safety',      type: 'Admin',      status: 'DISPUTED', amount: 3400.00,   balance: 54000.00 },
  { id: '#INV-2023-0885', date: '2023-10-15', projectRef: 'PRJ-A', description: 'Concrete Pour — Foundation Section B4 to B9',         type: 'Material',   status: 'CLEARED',  amount: 88200.00,  balance: 965500.00 },
  { id: '#PO-2023-438',   date: '2023-10-12', projectRef: 'PRJ-D', description: 'HVAC Duct Fabrication & Site Delivery (Phase 1)',      type: 'Subcontract',status: 'CLEARED',  amount: 32750.00,  balance: 441250.00 },
  { id: '#INV-2023-0878', date: '2023-10-09', projectRef: 'PRJ-B', description: 'Premium Terrazzo Flooring — Level 3 to Level 6',      type: 'Material',   status: 'PENDING',  amount: 56100.00,  balance: 1148400.00 },
  { id: '#FEE-2023-009',  date: '2023-10-07', projectRef: 'PRJ-C', description: 'Environmental Impact Assessment Consulting Fees',     type: 'Admin',      status: 'CLEARED',  amount: 9800.00,   balance: 44200.00 },
  { id: '#PO-2023-430',   date: '2023-10-05', projectRef: 'PRJ-A', description: 'Low-Voltage Cable Pull — Floors 10–20 (LSOH)',        type: 'Labor',      status: 'CLEARED',  amount: 27300.00,  balance: 938200.00 },
  { id: '#INV-2023-0871', date: '2023-10-02', projectRef: 'PRJ-D', description: 'Membrane Bioreactor UV Module Installation',          type: 'Equipment',  status: 'DISPUTED', amount: 142000.00, balance: 299250.00 },
  { id: '#PO-2023-421',   date: '2023-09-28', projectRef: 'PRJ-B', description: 'Smart Home Controller Units × 480 (Residential)',     type: 'Material',   status: 'CLEARED',  amount: 19200.00,  balance: 1185200.00 },
  { id: '#INV-2023-0865', date: '2023-09-25', projectRef: 'PRJ-A', description: 'Curtain Wall Panel Install — South Facade Block C',   type: 'Subcontract',status: 'CLEARED',  amount: 215000.00, balance: 723200.00 },
];

const PAGE_SIZE = 5;

const STATUS_STYLES: Record<RecordStatus, string> = {
  CLEARED:  'bg-emerald-100 text-emerald-700',
  PENDING:  'bg-amber-100 text-amber-700',
  DISPUTED: 'bg-red-100 text-red-700',
};

const SOURCE_OPTIONS  = ['All', 'Invoice', 'Purchase Order', 'Fee'];
const STATUS_OPTIONS  = ['Any', 'Cleared', 'Pending', 'Disputed'];
const DATE_OPTIONS    = ['Last 30 Days', 'Last 90 Days', 'This Year', 'All Time'];

export default function InsightsScreen({ projects }: InsightsScreenProps) {
  const [searchQuery,     setSearchQuery]     = useState('');
  const [selectedProject, setSelectedProject] = useState('All Projects');
  const [selectedSource,  setSelectedSource]  = useState('All');
  const [selectedStatus,  setSelectedStatus]  = useState('Any');
  const [selectedDate,    setSelectedDate]    = useState('Last 30 Days');
  const [currentPage,     setCurrentPage]     = useState(1);

  // Filter records
  const filtered = ALL_RECORDS.filter((r) => {
    const q = searchQuery.toLowerCase();
    const matchSearch  = !q || r.description.toLowerCase().includes(q) || r.id.toLowerCase().includes(q) || r.projectRef.toLowerCase().includes(q);
    const matchStatus  = selectedStatus === 'Any' || r.status === selectedStatus.toUpperCase();
    const matchSource  = selectedSource === 'All' ||
      (selectedSource === 'Invoice'        && r.id.startsWith('#INV')) ||
      (selectedSource === 'Purchase Order' && r.id.startsWith('#PO'))  ||
      (selectedSource === 'Fee'            && r.id.startsWith('#FEE'));
    return matchSearch && matchStatus && matchSource;
  });

  const totalPages  = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage    = Math.min(currentPage, totalPages);
  const pageRecords = filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const goPage = (p: number) => setCurrentPage(Math.max(1, Math.min(p, totalPages)));

  // Page number chips to show
  const pageNums: (number | '...')[] = [];
  if (totalPages <= 5) {
    for (let i = 1; i <= totalPages; i++) pageNums.push(i);
  } else {
    pageNums.push(1, 2, 3, '...', totalPages);
  }

  const handleExport = () => {
    const csv = [
      ['ID', 'Date', 'Project Ref', 'Description', 'Type', 'Status', 'Amount (USD)', 'Balance'].join(','),
      ...filtered.map((r) =>
        [r.id, r.date, r.projectRef, `"${r.description}"`, r.type, r.status, r.amount, r.balance].join(',')
      ),
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'data_warehouse.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div id="insights-view" className="space-y-6">

      {/* ── Page Title + Filters ─────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-sans font-bold text-[28px] text-zinc-900 tracking-tight leading-tight">
            Data Warehouse
          </h2>
          <p className="font-sans text-[13px] text-zinc-500 mt-1">
            Unified financial records and operational metrics.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2">
          {/* All Projects */}
          <div className="relative">
            <select
              id="insights-project-filter"
              value={selectedProject}
              onChange={(e) => { setSelectedProject(e.target.value); setCurrentPage(1); }}
              className="appearance-none pl-3 pr-8 py-2 text-[12px] font-sans font-medium text-zinc-700 bg-white border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 cursor-pointer shadow-xs"
            >
              <option>All Projects</option>
              {projects.map((p) => <option key={p.id}>{p.name}</option>)}
            </select>
            <ChevronDown className="absolute right-2 top-2.5 h-3.5 w-3.5 text-zinc-400 pointer-events-none" />
          </div>

          {/* Source */}
          <div className="relative">
            <select
              id="insights-source-filter"
              value={selectedSource}
              onChange={(e) => { setSelectedSource(e.target.value); setCurrentPage(1); }}
              className="appearance-none pl-3 pr-8 py-2 text-[12px] font-sans font-medium text-zinc-700 bg-white border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 cursor-pointer shadow-xs"
            >
              {SOURCE_OPTIONS.map((s) => <option key={s}>Source: {s}</option>)}
            </select>
            <ChevronDown className="absolute right-2 top-2.5 h-3.5 w-3.5 text-zinc-400 pointer-events-none" />
          </div>

          {/* Status */}
          <div className="relative">
            <select
              id="insights-status-filter"
              value={selectedStatus}
              onChange={(e) => { setSelectedStatus(e.target.value); setCurrentPage(1); }}
              className="appearance-none pl-3 pr-8 py-2 text-[12px] font-sans font-medium text-zinc-700 bg-white border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 cursor-pointer shadow-xs"
            >
              {STATUS_OPTIONS.map((s) => <option key={s}>Status: {s}</option>)}
            </select>
            <ChevronDown className="absolute right-2 top-2.5 h-3.5 w-3.5 text-zinc-400 pointer-events-none" />
          </div>

          {/* Date Range */}
          <div className="relative">
            <select
              id="insights-date-filter"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="appearance-none pl-8 pr-8 py-2 text-[12px] font-sans font-medium text-zinc-700 bg-white border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 cursor-pointer shadow-xs"
            >
              {DATE_OPTIONS.map((d) => <option key={d}>{d}</option>)}
            </select>
            <Calendar className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-zinc-400 pointer-events-none" />
            <ChevronDown className="absolute right-2 top-2.5 h-3.5 w-3.5 text-zinc-400 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* ── Export Button ─────────────────────────────────────────────────── */}
      <div>
        <button
          id="export-csv-btn"
          onClick={handleExport}
          className="flex items-center gap-2 px-5 py-2.5 bg-[#3F5E53] hover:bg-[#344E44] text-white font-sans font-semibold text-[13px] rounded-xl transition-all shadow-sm"
        >
          <Download className="h-4 w-4" />
          Export CSV/JSON
        </button>
      </div>

      {/* ── Data Table ────────────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="bg-white border border-zinc-200 rounded-2xl overflow-hidden shadow-xs"
      >
        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-zinc-200">
                {[
                  { label: 'ID',              cls: 'w-[140px]' },
                  { label: 'DATE',            cls: 'w-[110px]' },
                  { label: 'PROJECT REF',     cls: 'w-[100px]' },
                  { label: 'DESCRIPTION',     cls: '' },
                  { label: 'TYPE',            cls: 'w-[110px]' },
                  { label: 'STATUS',          cls: 'w-[110px]' },
                  { label: 'AMOUNT (USD)',    cls: 'w-[130px] text-right' },
                  { label: 'BALANCE',         cls: 'w-[120px] text-right' },
                ].map((col) => (
                  <th
                    key={col.label}
                    className={`px-5 py-3.5 font-sans font-bold text-[10px] text-zinc-500 uppercase tracking-widest ${col.cls}`}
                  >
                    {col.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {pageRecords.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-5 py-14 text-center">
                    <p className="font-sans text-sm text-zinc-400">No records match your filters.</p>
                  </td>
                </tr>
              ) : (
                pageRecords.map((rec, i) => (
                  <motion.tr
                    key={rec.id}
                    id={`record-row-${rec.id.replace('#', '').replace(/-/g, '_')}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.03 }}
                    className="hover:bg-zinc-50/70 transition-colors"
                  >
                    {/* ID */}
                    <td className="px-5 py-4">
                      <span className="font-mono text-[12px] font-semibold text-zinc-700">{rec.id}</span>
                    </td>

                    {/* Date */}
                    <td className="px-5 py-4">
                      <span className="font-sans text-[12px] text-zinc-600">{rec.date}</span>
                    </td>

                    {/* Project Ref */}
                    <td className="px-5 py-4">
                      <span className="font-mono text-[12px] font-semibold text-[#3F5E53]">{rec.projectRef}</span>
                    </td>

                    {/* Description */}
                    <td className="px-5 py-4 max-w-0">
                      <span
                        className="font-sans text-[12px] text-zinc-800 block truncate"
                        title={rec.description}
                      >
                        {rec.description.length > 38 ? rec.description.slice(0, 38) + '...' : rec.description}
                      </span>
                    </td>

                    {/* Type */}
                    <td className="px-5 py-4">
                      <span className="font-sans text-[12px] text-zinc-600">{rec.type}</span>
                    </td>

                    {/* Status */}
                    <td className="px-5 py-4">
                      <span className={`inline-block px-2.5 py-1 rounded font-mono text-[9px] font-bold uppercase tracking-wider ${STATUS_STYLES[rec.status]}`}>
                        {rec.status}
                      </span>
                    </td>

                    {/* Amount */}
                    <td className="px-5 py-4 text-right">
                      <span className="font-sans text-[12px] font-semibold text-zinc-900">
                        {rec.amount.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </span>
                    </td>

                    {/* Balance */}
                    <td className="px-5 py-4 text-right">
                      <span className="font-sans text-[12px] text-zinc-600">
                        {rec.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                      </span>
                    </td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* ── Pagination Footer ── */}
        <div className="flex items-center justify-between px-5 py-3.5 border-t border-zinc-100 bg-zinc-50/40">
          <span className="font-sans text-[12px] text-zinc-500">
            Showing {filtered.length === 0 ? 0 : (safePage - 1) * PAGE_SIZE + 1} to{' '}
            {Math.min(safePage * PAGE_SIZE, filtered.length)} of {filtered.length} entries
          </span>

          <div className="flex items-center gap-1">
            {/* Prev */}
            <button
              id="pagination-prev"
              onClick={() => goPage(safePage - 1)}
              disabled={safePage === 1}
              className="p-1.5 rounded-lg hover:bg-zinc-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="h-4 w-4 text-zinc-600" />
            </button>

            {/* Page numbers */}
            {pageNums.map((n, idx) =>
              n === '...' ? (
                <span key={`ellipsis-${idx}`} className="px-1.5 font-sans text-[12px] text-zinc-400">...</span>
              ) : (
                <button
                  key={n}
                  id={`pagination-page-${n}`}
                  onClick={() => goPage(n)}
                  className={`min-w-[30px] h-[30px] px-2 rounded-lg font-sans text-[12px] font-semibold transition-all ${
                    safePage === n
                      ? 'bg-[#3F5E53] text-white shadow-xs'
                      : 'text-zinc-600 hover:bg-zinc-100'
                  }`}
                >
                  {n}
                </button>
              )
            )}

            {/* Next */}
            <button
              id="pagination-next"
              onClick={() => goPage(safePage + 1)}
              disabled={safePage === totalPages}
              className="p-1.5 rounded-lg hover:bg-zinc-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="h-4 w-4 text-zinc-600" />
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
