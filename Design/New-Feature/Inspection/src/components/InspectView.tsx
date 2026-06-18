/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef } from "react";
import {
  Upload,
  Plus,
  Minus,
  Lightbulb,
  PlusCircle,
  Edit,
  X,
  AlertCircle
} from "lucide-react";
import { Defect, DefectSeverity, DefectStatus } from "../types";
import { zoneList, quickAddPresets } from "../data";

interface InspectViewProps {
  defects: Defect[];
  addDefect: (defect: Omit<Defect, "id">) => void;
  activeZone: string;
  setActiveZone: (zone: string) => void;
}

export default function InspectView({
  defects,
  addDefect,
  activeZone,
  setActiveZone
}: InspectViewProps) {
  const [scale, setScale] = useState(1);
  const [showAddModal, setShowAddModal] = useState(false);
  const [clickCoordinates, setClickCoordinates] = useState({ x: 50, y: 50 });
  const [hoveredDefectId, setHoveredDefectId] = useState<string | null>(null);

  // Form states for new custom defect pin
  const [newDesc, setNewDesc] = useState("");
  const [newCategory, setNewCategory] = useState("Architectural");
  const [newSeverity, setNewSeverity] = useState<DefectSeverity>(DefectSeverity.MINOR);
  const [newResponsible, setNewResponsible] = useState("Apex Builders Ltd.");
  const [newDetails, setNewDetails] = useState("");

  const mapContainerRef = useRef<HTMLDivElement>(null);

  // Filter defects for the current floor level/zone
  const currentZoneDefects = defects.filter(
    (d) => d.zone === activeZone && d.status !== DefectStatus.RESOLVED
  );

  // Total unclosed for score
  const totalZoneDefects = defects.filter((d) => d.zone === activeZone).length;
  const resolvedZoneDefects = defects.filter(
    (d) => d.zone === activeZone && d.status === DefectStatus.RESOLVED
  ).length;

  const zoneReadinessScore =
    totalZoneDefects > 0
      ? Math.round(85 + (resolvedZoneDefects / totalZoneDefects) * 15)
      : 85;

  // Handle map click to drop a pin
  const handleMapClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!mapContainerRef.current) return;
    const rect = mapContainerRef.current.getBoundingClientRect();
    const clickX = ((e.clientX - rect.left) / rect.width) * 100;
    const clickY = ((e.clientY - rect.top) / rect.height) * 100;

    setClickCoordinates({ x: Math.round(clickX), y: Math.round(clickY) });
    setNewDesc("");
    setNewDetails("");
    setShowAddModal(true);
  };

  // Create new defect from map coordinate click
  const handleSubmitCustomDefect = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDesc.trim()) return;

    addDefect({
      description: newDesc,
      category: newCategory,
      severity: newSeverity,
      responsibleParty: newResponsible,
      dueDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0], // 1 week out
      status: DefectStatus.OPEN,
      zone: activeZone,
      x: clickCoordinates.x,
      y: clickCoordinates.y,
      details: newDetails
    });

    setShowAddModal(false);
  };

  // Quick add defect handler
  const handleQuickAdd = (preset: typeof quickAddPresets[0]) => {
    // Generate a random position on the map layout safely
    const randomX = Math.round(15 + Math.random() * 70);
    const randomY = Math.round(15 + Math.random() * 70);

    addDefect({
      description: preset.description,
      category: preset.category,
      severity: preset.severity,
      responsibleParty: "Apex Builders Ltd.",
      dueDate: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
      status: DefectStatus.OPEN,
      zone: activeZone,
      x: randomX,
      y: randomY,
      details: "Quick add preset inspection tag."
    });
  };

  // Helper colors for pins
  const getSeverityColor = (severity: DefectSeverity) => {
    switch (severity) {
      case DefectSeverity.CRITICAL:
        return "bg-brand-error text-white";
      case DefectSeverity.MAJOR:
        return "bg-[#f59e0b] text-white";
      case DefectSeverity.MINOR:
        return "bg-[#eab308] text-white";
      default:
        return "bg-brand-outline text-white";
    }
  };

  return (
    <div className="space-y-6 animate-fade-in pb-10">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end pb-4 border-b border-brand-border-subtle gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-brand-on-surface mb-1">
            Site Inspection
          </h1>
          <p className="text-base text-brand-on-surface-variant font-medium">
            {activeZone}
          </p>
        </div>
        <div className="flex flex-wrap gap-3 items-center w-full sm:w-auto">
          <select
            value={activeZone}
            onChange={(e) => setActiveZone(e.target.value)}
            className="border border-brand-border-subtle rounded-md px-4 py-2 bg-brand-surface text-brand-on-surface font-semibold text-sm focus:ring-2 focus:ring-brand-primary focus:border-brand-primary outline-hidden cursor-pointer"
          >
            {zoneList.map((zone) => (
              <option key={zone} value={zone}>
                {zone}
              </option>
            ))}
          </select>

          <button
            onClick={() => {
              const confirmUpload = confirm("Simulate Project Floor Plan Upload?\nReady to parse structural DWG/PDF file layout.");
              if (confirmUpload) {
                alert("Floor plan imported successfully!\nActive layers registered.");
              }
            }}
            className="flex items-center gap-2 px-4 py-2 border border-brand-border-subtle rounded-md hover:bg-brand-surface-container-low transition-colors font-bold text-xs text-brand-on-surface bg-brand-surface cursor-pointer"
          >
            <Upload className="w-4 h-4 text-brand-outline" />
            Upload Plan
          </button>
        </div>
      </div>

      {/* Two Column Interactive Stage */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left Interactive Blueprint Map Area (65%) */}
        <div className="w-full lg:w-[65%] bg-brand-surface border border-brand-border-subtle rounded-lg flex flex-col relative overflow-hidden group min-h-[480px]">
          {/* Legend and Card Header */}
          <div className="p-4 border-b border-brand-border-subtle flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 bg-brand-surface-container-lowest z-10 font-bold text-xs">
            <h2 className="text-sm font-bold text-brand-on-surface">
              Interactive Floor Plan
            </h2>
            <div className="flex flex-wrap gap-3 font-semibold text-brand-on-surface-variant">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-brand-error inline-block" />
                Critical ({currentZoneDefects.filter((d) => d.severity === DefectSeverity.CRITICAL).length})
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-[#f59e0b] inline-block" />
                Major ({currentZoneDefects.filter((d) => d.severity === DefectSeverity.MAJOR).length})
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full bg-[#eab308] inline-block" />
                Minor ({currentZoneDefects.filter((d) => d.severity === DefectSeverity.MINOR).length})
              </span>
            </div>
          </div>

          <div
            ref={mapContainerRef}
            onClick={handleMapClick}
            className="flex-1 relative bg-brand-surface-container-low overflow-hidden cursor-crosshair min-h-[360px]"
            title="Click anywhere on the blueprint to file a core inspection defect pin!"
          >
            {/* Floor plan blueprint picture layout */}
            <div
              className="absolute inset-0 bg-cover bg-center transition-transform duration-300"
              style={{
                backgroundImage:
                  "url('https://lh3.googleusercontent.com/aida-public/AB6AXuAQaOeQeo8NBt7dyPcXOd5r4tpF0ynQsRLLUuUKcAQ73XeITUJ3IfRZRfzeo3F7hE0lZvmqlmYE59lUxEdezaOBdvsD_EiIUyDga-EBPjcU-u_pHjCwPE8BOKuWMT4v5KurT8wS1p00W1hr36lhlz73kjFpmmDGSvWp-8trQkxvCJJlTorJVPYrHqhi8qpse-uqu0FuqivmZ4JMoDkBhssY0p6r2zf2bHbiy3IoKUxxyBBG7b6mqfkjVl0C3BUoO2PejNT0VjO1qfQ')",
                transform: `scale(${scale})`,
                opacity: 0.8
              }}
            />
            {/* White Dim glass layout */}
            <div className="absolute inset-0 bg-white/45 backdrop-blur-[1px] pointer-events-none" />

            {/* Simulated instructions label */}
            <div className="absolute top-4 left-4 bg-brand-primary-container text-brand-on-primary text-[10px] font-bold px-3 py-1.5 rounded-full shadow-md z-1">
              💡 Hint: Click anywhere on the map to add a custom pin
            </div>

            {/* Render Defects Pins */}
            {currentZoneDefects.map((defect, idx) => (
              <div
                key={defect.id}
                onClick={(e) => {
                  e.stopPropagation(); // Avoid triggering map coordinate click
                  alert(`In-depth Defect details (${defect.id}):\nDescription: ${defect.description}\nCategory: ${defect.category}\nSeverity: ${defect.severity}\nStatus: ${defect.status}\nAssigned: ${defect.responsibleParty}\nDetail fields: ${defect.details || "No secondary comments registered."}`);
                }}
                onMouseEnter={() => setHoveredDefectId(defect.id)}
                onMouseLeave={() => setHoveredDefectId(null)}
                className="absolute transition-all z-10"
                style={{
                  left: `${defect.x}%`,
                  top: `${defect.y}%`,
                  transform: "translate(-50%, -50%)"
                }}
              >
                <button
                  type="button"
                  className={`w-8 h-8 rounded-full font-bold shadow-md border-2 border-brand-surface flex items-center justify-center hover:scale-110 active:scale-95 transition-all ${getSeverityColor(
                    defect.severity
                  )}`}
                >
                  {idx + 1}
                </button>

                {/* Tooltip Hover Overlay */}
                {hoveredDefectId === defect.id && (
                  <div className="absolute top-10 left-1/2 -translate-x-1/2 bg-brand-surface border border-brand-border-subtle p-3 rounded-md shadow-xl w-52 z-30 pointer-events-none">
                    <p className="font-bold text-xs text-brand-on-background mb-0.5">
                      {defect.id}
                    </p>
                    <p className="font-bold text-xs text-brand-secondary mb-1">
                      {defect.description}
                    </p>
                    <p className="text-[10px] text-brand-on-surface-variant font-medium leading-normal">
                      Category: {defect.category} • {defect.severity}
                    </p>
                    <p className="text-[9px] text-brand-outline italic mt-1 font-semibold">
                      Click pin for detailed comments.
                    </p>
                  </div>
                )}
              </div>
            ))}

            {/* Map zoom controls */}
            <div className="absolute bottom-4 right-4 flex flex-col gap-1 bg-brand-surface p-1 rounded-lg border border-brand-border-subtle shadow-md z-10">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setScale((prev) => Math.min(prev + 0.25, 2.5));
                }}
                className="p-1 text-brand-on-surface-variant hover:text-brand-primary hover:bg-brand-surface-container-low rounded-md transition-colors cursor-pointer"
                title="Zoom In"
              >
                <Plus className="w-4 h-4" />
              </button>
              <div className="h-px bg-brand-border-subtle w-full" />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setScale((prev) => Math.max(prev - 0.25, 0.75));
                }}
                className="p-1 text-brand-on-surface-variant hover:text-brand-primary hover:bg-brand-surface-container-low rounded-md transition-colors cursor-pointer"
                title="Zoom Out"
              >
                <Minus className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Right Side: Metrics & Quickadd Options (35%) */}
        <div className="w-full lg:w-[35%] flex flex-col gap-6 overflow-y-auto pr-1">
          {/* Score & Defects counts metrics row */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-brand-surface border border-brand-border-subtle p-4 rounded-lg shadow-xs">
              <h3 className="text-[11px] font-bold text-brand-outline uppercase tracking-wider mb-2">
                Zone Readiness
              </h3>
              <div className="flex items-end gap-1.5">
                <span className="text-3xl font-bold text-brand-primary">
                  {zoneReadinessScore}
                </span>
                <span className="text-xs font-semibold text-brand-on-surface-variant pb-1">
                  / 100
                </span>
              </div>
              <div className="w-full bg-brand-surface-container-high h-1.5 mt-3 rounded-full overflow-hidden">
                <div
                  className="bg-brand-primary h-full rounded-full transition-all duration-300"
                  style={{ width: `${zoneReadinessScore}%` }}
                ></div>
              </div>
            </div>

            <div className="bg-brand-surface border border-brand-border-subtle p-4 rounded-lg shadow-xs">
              <h3 className="text-[11px] font-bold text-brand-outline uppercase tracking-wider mb-2">
                Open Defects
              </h3>
              <div className="flex items-end gap-1.5">
                <span className="text-3xl font-bold text-brand-error">
                  {currentZoneDefects.length}
                </span>
              </div>
              <p className="text-[10px] font-semibold text-brand-error mt-2.5">
                Requires active containment
              </p>
            </div>
          </div>

          {/* Machine Recommendations Advice Box */}
          <div className="bg-brand-surface-container-low border border-brand-primary-fixed-dim p-4 rounded-lg relative overflow-hidden shadow-xs">
            <div className="absolute top-0 left-0 w-1 h-full bg-brand-primary" />
            <div className="flex items-start gap-3">
              <Lightbulb className="w-5 h-5 text-brand-primary shrink-0 mt-0.5 animate-pulse" />
              <div>
                <h3 className="font-bold text-xs text-brand-primary uppercase tracking-wider mb-1">
                  Recommendation
                </h3>
                <p className="text-xs text-brand-on-surface-variant leading-relaxed">
                  Focus inspections on <strong>HVAC ducting</strong> in the North corridor.
                  Previous finished levels showed a 40% failure rate for seal integrity in similar zones.
                </p>
              </div>
            </div>
          </div>

          {/* Quick Preset Buttons */}
          <div className="bg-brand-surface border border-brand-border-subtle rounded-lg flex flex-col shadow-xs">
            <div className="p-4 border-b border-brand-border-subtle bg-brand-surface-container-low rounded-t-lg">
              <h3 className="text-sm font-bold text-brand-on-surface">
                Quick Add Defect
              </h3>
              <p className="text-[11px] text-brand-on-surface-variant font-medium mt-0.5">
                Common issues found on site
              </p>
            </div>
            <div className="flex flex-col divide-y divide-brand-border-subtle">
              {quickAddPresets.map((preset) => (
                <button
                  key={preset.description}
                  onClick={() => handleQuickAdd(preset)}
                  className="flex items-center justify-between p-3.5 hover:bg-brand-surface-container-lowest transition-colors text-left group cursor-pointer"
                >
                  <div>
                    <span className="text-xs font-bold text-brand-on-surface block">
                      {preset.description}
                    </span>
                    <span className="text-[10px] text-brand-on-surface-variant font-medium mt-0.5 block">
                      {preset.category} • {preset.severity}
                    </span>
                  </div>
                  <PlusCircle className="w-5 h-5 text-brand-border-subtle group-hover:text-brand-primary transition-colors shrink-0 ml-3" />
                </button>
              ))}
            </div>

            <div className="p-3 bg-brand-surface-container-low border-t border-brand-border-subtle text-center">
              <button
                onClick={() => {
                  setClickCoordinates({ x: 50, y: 50 });
                  setNewDesc("");
                  setNewDetails("");
                  setShowAddModal(true);
                }}
                className="w-full py-2 text-brand-primary font-bold text-xs hover:bg-brand-surface-container-highest rounded-lg transition-colors flex items-center justify-center gap-2 cursor-pointer"
              >
                <Edit className="w-4 h-4" />
                Custom Entry
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Add Custom Defect Modal Popover overlay */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-[#fdf9f5] border border-brand-border-subtle rounded-xl max-w-md w-full shadow-2xl overflow-hidden p-6 relative animate-fade-in text-brand-on-background">
            <button
              onClick={() => setShowAddModal(false)}
              className="absolute top-4 right-4 text-brand-on-surface-variant hover:text-brand-on-background cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <h3 className="text-lg font-bold text-brand-primary flex items-center gap-2 mb-2">
              <AlertCircle className="w-5 h-5 text-brand-primary" />
              Report Defect Pin
            </h3>
            <p className="text-xs text-brand-on-surface-variant font-medium mb-4">
              Dropping inspection marker at coordinate (x: {clickCoordinates.x}%, y: {clickCoordinates.y}%).
            </p>

            <form onSubmit={handleSubmitCustomDefect} className="space-y-4">
              <div>
                <label className="block text-xs font-bold tracking-wider uppercase text-brand-on-surface-variant mb-1">
                  Description
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Broken wall molding seam"
                  className="w-full px-3 py-2 border border-brand-border-subtle rounded bg-brand-surface text-sm focus:ring-2 focus:ring-brand-primary outline-hidden"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold tracking-wider uppercase text-brand-on-surface-variant mb-1">
                    Category
                  </label>
                  <select
                    className="w-full px-3 py-2 border border-brand-border-subtle rounded bg-brand-surface text-sm focus:ring-2 focus:ring-brand-primary cursor-pointer font-semibold"
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                  >
                    <option value="Architectural">Architectural</option>
                    <option value="Electrical">Electrical</option>
                    <option value="Plumbing">Plumbing</option>
                    <option value="Mechanical / HVAC">Mechanical / HVAC</option>
                    <option value="Finishes">Finishes</option>
                    <option value="Carpentry">Carpentry</option>
                    <option value="Structural">Structural</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold tracking-wider uppercase text-brand-on-surface-variant mb-1">
                    Severity
                  </label>
                  <select
                    className="w-full px-3 py-2 border border-brand-border-subtle rounded bg-brand-surface text-sm focus:ring-2 focus:ring-brand-primary cursor-pointer font-semibold"
                    value={newSeverity}
                    onChange={(e) => setNewSeverity(e.target.value as DefectSeverity)}
                  >
                    <option value={DefectSeverity.CRITICAL}>Critical</option>
                    <option value={DefectSeverity.MAJOR}>Major</option>
                    <option value={DefectSeverity.MINOR}>Minor</option>
                    <option value={DefectSeverity.COSMETIC}>Cosmetic</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold tracking-wider uppercase text-brand-on-surface-variant mb-1">
                  Responsible Party
                </label>
                <input
                  type="text"
                  required
                  className="w-full px-3 py-2 border border-brand-border-subtle rounded bg-brand-surface text-sm focus:ring-2 focus:ring-brand-primary outline-hidden"
                  value={newResponsible}
                  onChange={(e) => setNewResponsible(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-xs font-bold tracking-wider uppercase text-brand-on-surface-variant mb-1 text-left">
                  Additional Details / Comment
                </label>
                <textarea
                  rows={2}
                  placeholder="Describe location details or instructions..."
                  className="w-full px-3 py-2 border border-brand-border-subtle rounded bg-brand-surface text-xs focus:ring-2 focus:ring-brand-primary outline-hidden"
                  value={newDetails}
                  onChange={(e) => setNewDetails(e.target.value)}
                />
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-brand-border-subtle rounded text-xs font-bold hover:bg-brand-surface-container-low cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-brand-primary text-brand-on-primary rounded text-xs font-bold hover:bg-brand-surface-tint shadow-xs cursor-pointer"
                >
                  Add Defect Marker
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
