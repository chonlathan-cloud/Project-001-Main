/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from "react";
import {
  Search,
  Filter,
  CheckCircle2,
  AlertOctagon,
  Image,
  ImageIcon,
  MoreVertical,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Trash2,
  Check
} from "lucide-react";
import { Defect, DefectSeverity, DefectStatus } from "../types";

interface DefectsViewProps {
  defects: Defect[];
  updateDefectStatus: (id: string, status: DefectStatus) => void;
  deleteDefect: (id: string) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
}

export default function DefectsView({
  defects,
  updateDefectStatus,
  deleteDefect,
  searchQuery,
  setSearchQuery
}: DefectsViewProps) {
  const [statusFilter, setStatusFilter] = useState<string>("All");
  const [severityFilter, setSeverityFilter] = useState<string>("All");
  const [activeActionId, setActiveActionId] = useState<string | null>(null);

  // Pagination states
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // Filter local logic
  const filteredDefects = defects.filter((defect) => {
    const matchesSearch =
      defect.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      defect.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      defect.responsibleParty.toLowerCase().includes(searchQuery.toLowerCase()) ||
      defect.category.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus =
      statusFilter === "All" || defect.status === statusFilter;

    const matchesSeverity =
      severityFilter === "All" || defect.severity === severityFilter;

    return matchesSearch && matchesStatus && matchesSeverity;
  });

  // Pagination indexing
  const totalItems = filteredDefects.length;
  const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedDefects = filteredDefects.slice(startIndex, startIndex + itemsPerPage);

  const getSeverityBadgeClass = (severity: DefectSeverity) => {
    switch (severity) {
      case DefectSeverity.CRITICAL:
        return "bg-brand-error-container text-brand-on-error-container border border-red-200";
      case DefectSeverity.MAJOR:
        return "bg-orange-100 text-orange-800 border border-orange-200";
      case DefectSeverity.MINOR:
        return "bg-yellow-100 text-yellow-800 border border-yellow-200";
      default:
        return "bg-brand-surface-container-high text-brand-on-surface-variant border border-brand-border-subtle";
    }
  };

  const getStatusBadge = (status: DefectStatus) => {
    switch (status) {
      case DefectStatus.OPEN:
        return (
          <span className="inline-flex items-center gap-1.5 text-xs text-brand-error font-bold">
            <span className="w-2.5 h-2.5 rounded-full bg-brand-error animate-pulse" />
            Open
          </span>
        );
      case DefectStatus.IN_PROGRESS:
        return (
          <span className="inline-flex items-center gap-1.5 text-xs text-yellow-600 font-bold">
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
            In Progress
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 text-xs text-brand-primary font-bold opacity-80">
            <CheckCircle2 className="w-4 h-4 text-brand-primary inline" />
            Resolved
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 animate-fade-in pb-10">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-2 gap-4">
        <div>
          <h2 className="text-3xl font-extrabold text-brand-on-background">Defects</h2>
          <p className="text-sm font-medium text-brand-text-secondary mt-1">
            Manage and track all reported site issues.
          </p>
        </div>

        {/* Quick Dropdown Actions Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-brand-surface border border-brand-border-subtle rounded-lg px-3 py-1.5 text-xs font-semibold text-brand-on-surface">
            <Filter className="w-3.5 h-3.5 text-brand-outline" />
            <span>Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-transparent border-none p-0 focus:ring-0 cursor-pointer font-bold outline-hidden"
            >
              <option value="All">All Statuses</option>
              <option value={DefectStatus.OPEN}>Open</option>
              <option value={DefectStatus.IN_PROGRESS}>In Progress</option>
              <option value={DefectStatus.RESOLVED}>Resolved</option>
            </select>
          </div>

          <div className="flex items-center gap-2 bg-brand-surface border border-brand-border-subtle rounded-lg px-3 py-1.5 text-xs font-semibold text-brand-on-surface">
            <AlertOctagon className="w-3.5 h-3.5 text-brand-outline" />
            <span>Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="bg-transparent border-none p-0 focus:ring-0 cursor-pointer font-bold outline-hidden"
            >
              <option value="All">All Severities</option>
              <option value={DefectSeverity.CRITICAL}>Critical</option>
              <option value={DefectSeverity.MAJOR}>Major</option>
              <option value={DefectSeverity.MINOR}>Minor</option>
              <option value={DefectSeverity.COSMETIC}>Cosmetic</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Table card */}
      <div className="bg-brand-surface border border-brand-border-subtle rounded-xl shadow-xs overflow-hidden">
        {/* Dynamic Search block within Table control rail for smaller displays */}
        <div className="p-4 bg-brand-surface-container-low border-b border-brand-border-subtle flex flex-col sm:flex-row justify-between items-center gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3 top-2.5 w-4 h-4 text-brand-outline" />
            <input
              type="text"
              placeholder="Filter catalog content..."
              className="w-full pl-9 pr-4 py-1.5 text-xs border border-brand-border-subtle rounded-md bg-brand-surface text-brand-on-surface outline-hidden focus:ring-2 focus:ring-brand-primary"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
            />
          </div>
          <p className="text-xs text-brand-on-surface-variant font-semibold">
            Showing <span className="text-brand-primary font-bold">{totalItems}</span> matching item(s) on-site
          </p>
        </div>

        {/* Scrollable table container */}
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-left text-sm border-collapse">
            <thead className="bg-[#f0ece9] border-b border-brand-border-subtle text-xs font-bold uppercase tracking-wider text-brand-on-surface-variant">
              <tr>
                <th className="p-4">ID</th>
                <th className="p-4 w-12 text-center">Clip</th>
                <th className="p-4 min-w-[220px]">Description</th>
                <th className="p-4">Category</th>
                <th className="p-4">Severity</th>
                <th className="p-4">Zone</th>
                <th className="p-4">Responsible Party</th>
                <th className="p-4">Due Date</th>
                <th className="p-4">Status</th>
                <th className="p-4 w-12 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-border-subtle text-xs text-brand-on-background">
              {paginatedDefects.length === 0 ? (
                <tr>
                  <td colSpan={10} className="p-8 text-center text-brand-on-surface-variant font-medium">
                    No matching site defects found matching the filter criteria.
                  </td>
                </tr>
              ) : (
                paginatedDefects.map((defect) => {
                  const isClosed = defect.status === DefectStatus.RESOLVED;
                  return (
                    <tr
                      key={defect.id}
                      className={`hover:bg-[#faf6f2] transition-colors ${
                        isClosed ? "bg-blend-luminosity opacity-75" : ""
                      }`}
                    >
                      {/* ID */}
                      <td className="p-4 font-mono font-bold text-brand-outline">
                        {defect.id}
                      </td>

                      {/* Photo block */}
                      <td className="p-4">
                        {defect.pictureUrl ? (
                          <div className="w-10 h-10 rounded-md border border-brand-border-subtle overflow-hidden bg-brand-surface-container shadow-xs">
                            <img
                              alt={defect.description}
                              className="w-full h-full object-cover"
                              referrerPolicy="no-referrer"
                              src={defect.pictureUrl}
                            />
                          </div>
                        ) : (
                          <div className="w-10 h-10 rounded-md border border-brand-border-subtle bg-brand-surface-container-high flex items-center justify-center placeholder-svg">
                            <ImageIcon className="w-5 h-5 text-brand-outline" />
                          </div>
                        )}
                      </td>

                      {/* Description */}
                      <td className="p-4 font-bold text-brand-on-surface text-xs max-w-xs truncate">
                        <div>{defect.description}</div>
                        {defect.details && (
                          <span className="block font-medium text-[10px] text-brand-outline italic mt-0.5">
                            {defect.details}
                          </span>
                        )}
                      </td>

                      {/* Category */}
                      <td className="p-4 font-semibold text-brand-on-surface-variant">
                        {defect.category}
                      </td>

                      {/* Severity badge */}
                      <td className="p-4">
                        <span
                          className={`inline-block px-2.5 py-1 text-[9px] font-bold uppercase tracking-wider rounded-md ${getSeverityBadgeClass(
                            defect.severity
                          )}`}
                        >
                          {defect.severity}
                        </span>
                      </td>

                      {/* Zone Level */}
                      <td className="p-4 font-semibold text-brand-outline">
                        {defect.zone}
                      </td>

                      {/* Assigned party */}
                      <td className="p-4 font-bold text-brand-on-surface-variant">
                        {defect.responsibleParty}
                      </td>

                      {/* Due date */}
                      <td className="p-4 text-brand-outline tabular-nums font-semibold">
                        {defect.dueDate}
                      </td>

                      {/* Interactive Status Indicator */}
                      <td className="p-4">{getStatusBadge(defect.status)}</td>

                      {/* Dynamic action dropdown */}
                      <td className="p-4 text-center relative">
                        <button
                          onClick={() => {
                            setActiveActionId(
                              activeActionId === defect.id ? null : defect.id
                            );
                          }}
                          className="p-1.5 text-brand-outline hover:text-brand-on-surface hover:bg-brand-surface-container rounded-md transition-colors cursor-pointer"
                        >
                          <MoreVertical className="w-4 h-4" />
                        </button>

                        {/* Settings Context menu popup */}
                        {activeActionId === defect.id && (
                          <div className="absolute right-12 top-2 bg-[#fdf9f5] border border-brand-border-subtle p-2 rounded-lg shadow-xl w-40 z-30 text-left">
                            <span className="block text-[10px] font-bold text-brand-outline mb-1.5 uppercase px-2 tracking-wide">
                              Update Status
                            </span>
                            <div className="space-y-0.5">
                              {Object.values(DefectStatus).map((status) => (
                                <button
                                  key={status}
                                  onClick={() => {
                                    updateDefectStatus(defect.id, status);
                                    setActiveActionId(null);
                                  }}
                                  className={`w-full text-left px-2 py-1.5 text-xs font-semibold rounded-md flex items-center justify-between hover:bg-brand-surface-container-low cursor-pointer ${
                                    defect.status === status
                                      ? "text-brand-primary"
                                      : "text-brand-on-surface-variant"
                                  }`}
                                >
                                  {status}
                                  {defect.status === status && (
                                    <Check className="w-3.5 h-3.5 text-brand-primary" />
                                  )}
                                </button>
                              ))}
                            </div>
                            <div className="h-px bg-brand-border-subtle my-1.5" />
                            <button
                              onClick={() => {
                                if (confirm(`Confirm deletion of inspection item ${defect.id}?`)) {
                                  deleteDefect(defect.id);
                                }
                                setActiveActionId(null);
                              }}
                              className="w-full text-left px-2 py-1.5 text-xs font-semibold text-brand-error rounded-md flex items-center gap-2 hover:bg-red-50 cursor-pointer"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              Delete Pin
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="bg-brand-surface border-t border-brand-border-subtle p-4 flex items-center justify-between text-xs font-semibold text-brand-text-secondary">
          <div>
            Showing <span className="font-bold text-brand-primary">{startIndex + 1}</span> to{" "}
            <span className="font-bold text-brand-primary">
              {Math.min(startIndex + itemsPerPage, totalItems)}
            </span>{" "}
            of <span className="font-bold">{totalItems}</span> defects
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1 rounded-md border border-brand-border-subtle text-brand-outline hover:bg-brand-surface-container transition-colors disabled:opacity-40 cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-brand-on-surface-variant">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1 rounded-md border border-brand-border-subtle text-brand-outline hover:bg-brand-surface-container transition-colors disabled:opacity-40 cursor-pointer"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
