import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Plus, CheckCircle, AlertTriangle, RefreshCw, Calendar, MapPin, Search, ArrowLeft, Database, HardDriveUpload, Check, X, FileSpreadsheet, Building } from 'lucide-react';
import { Project, BOQItem, ProjectStatus } from '../types';

interface ProjectsScreenProps {
  projects: Project[];
  onAddProject: (newProj: Project) => void;
  onUpdateProject: (updatedProj: Project) => void;
  onAddActivity: (msg: string, code: string, name: string, type: 'sync' | 'budget_alteration') => void;
  isNewProjectModalOpen: boolean;
  setIsNewProjectModalOpen: (open: boolean) => void;
}

export default function ProjectsScreen({
  projects,
  onAddProject,
  onUpdateProject,
  onAddActivity,
  isNewProjectModalOpen,
  setIsNewProjectModalOpen,
}: ProjectsScreenProps) {
  // Navigation states inside Projects Screen
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSyncDrawerOpen, setIsSyncDrawerOpen] = useState(false);
  
  // Syncing states
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncLogs, setSyncLogs] = useState<string[]>([]);
  
  // Create Project states
  const [newName, setNewName] = useState('');
  const [newCode, setNewCode] = useState('PRJ-001-E');
  const [newBudget, setNewBudget] = useState('18000000');
  const [newOwner, setNewOwner] = useState('John Doe (Director)');
  const [newLocation, setNewLocation] = useState('North Industrial Corridor');
  const [newDescription, setNewDescription] = useState('');

  // Find active selected project details
  const activeDetailProject = projects.find((p) => p.id === selectedProjectId);

  // Filtered project list
  const filteredProjects = projects.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.owner.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatCurrency = (val: number) => {
    return `$${val.toLocaleString()}`;
  };

  const getStatusComponent = (status: ProjectStatus) => {
    switch (status) {
      case 'active':
        return (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wide font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-150">
            Active Block
          </span>
        );
      case 'draft':
        return (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wide font-semibold text-zinc-500 bg-zinc-100 px-2 py-0.5 rounded border border-zinc-200">
            Draft Spec
          </span>
        );
      case 'on_hold':
        return (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wide font-semibold text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
            On Hold
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wide font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-250">
            Released
          </span>
        );
    }
  };

  // Submit/Add New Project
  const handleCreateProjectSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;

    const newProj: Project = {
      id: `PRJ-${Math.floor(100 + Math.random() * 900)}`,
      name: newName,
      code: newCode,
      status: 'draft',
      budget: parseFloat(newBudget) || 100000,
      spent: 0,
      progress: 0,
      owner: newOwner,
      subcontractorCount: 0,
      startDate: new Date().toISOString().split('T')[0],
      endDate: '2028-12-30',
      description: newDescription || 'Standard contractual development initialized under parent Projects-001.',
      boqSynced: false,
      location: newLocation,
      boqItems: [],
    };

    onAddProject(newProj);
    setIsNewProjectModalOpen(false);

    // Reset fields
    setNewName('');
    setNewCode(`PRJ-001-${String.fromCharCode(70 + Math.floor(Math.random() * 10))}`);
    setNewBudget('12000000');
    setNewDescription('');
  };

  // Run Autodesk/Spreadsheet synchronization simulation
  const triggerBOQSync = () => {
    if (!activeDetailProject) return;
    setIsSyncing(true);
    setSyncLogs(['Establishing connection to Autodesk BIM 360...', 'Querying Revit Structural Quantities module...']);

    setTimeout(() => {
      setSyncLogs((prev) => [...prev, 'Comparing 14 database nodes against current BOQ...']);
    }, 1000);

    setTimeout(() => {
      setSyncLogs((prev) => [...prev, 'Updating unit amounts & generating ledger variance logs...']);
    }, 2000);

    setTimeout(() => {
      // Create a simulated synced list of BOQ items if empty or update they status
      const updatedBOQ: BOQItem[] = activeDetailProject.boqItems.length === 0 ? [
        { id: 'boq-sync-1', itemCode: '03.2000', description: 'Simulated Sycned Foundation Steel Base Rebar', unit: 'ton', quantity: 180, rate: 1950, amount: 351000, status: 'synced' },
        { id: 'boq-sync-2', itemCode: '04.2200', description: 'Concrete masonry masonry blocks (200mm thick)', unit: 'm2', quantity: 4500, rate: 65, amount: 292500, status: 'synced' },
        { id: 'boq-sync-3', itemCode: '07.2100', description: 'Thermal mineral wool batt insulation', unit: 'm2', quantity: 12000, rate: 14, amount: 168000, status: 'synced' }
      ] : activeDetailProject.boqItems.map(item => ({ ...item, status: 'synced' }));

      const currentTimestamp = new Date().toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
        hour12: true
      });

      const updatedProj: Project = {
        ...activeDetailProject,
        boqSynced: true,
        boqLastSync: `${currentTimestamp}`,
        subcontractorCount: activeDetailProject.subcontractorCount || 3,
        boqItems: updatedBOQ
      };

      onUpdateProject(updatedProj);
      onAddActivity(
        `Synchronized ${updatedBOQ.length} structural lines in BOQ with Revit BIM 360 schema`,
        updatedProj.code,
        updatedProj.name,
        'sync'
      );

      setIsSyncing(false);
      setIsSyncDrawerOpen(false);
    }, 3500);
  };

  return (
    <div id="projects-view" className="space-y-8 relative">
      <AnimatePresence mode="wait">
        {!selectedProjectId ? (
          /* ========================================================================= */
          /* 1. PRIMARY ACTIVE PROJECTS ENTITIES LISTING                                */
          /* ========================================================================= */
          <motion.div
            key="list"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            className="space-y-6"
          >
            {/* Header info */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <h2 className="font-sans font-bold text-3xl text-zinc-900 tracking-tight">Structural Entities</h2>
                <p className="font-mono text-xs text-zinc-500 mt-1">Select an active or drafted construction program to verify BOQ specifications</p>
              </div>
              <button
                id="open-new-project-modal-btn"
                onClick={() => setIsNewProjectModalOpen(true)}
                className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white font-medium text-xs rounded-lg flex items-center gap-1.5 transition-all shadow-sm"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Initialize Project</span>
              </button>
            </div>

            {/* Program filtering/search */}
            <div className="relative max-w-md bg-white border border-zinc-200 rounded-xl overflow-hidden shadow-2xs">
              <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-zinc-400" />
              <input
                id="projects-grid-search"
                type="text"
                placeholder="Search projects, engineers, or identifiers..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 text-xs font-sans rounded-xl bg-zinc-50 hover:bg-white text-zinc-800 focus:outline-none transition-all"
              />
            </div>

            {/* Projects entities grid */}
            <div id="projects-grid" className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {filteredProjects.map((p) => {
                const specRatio = p.budget > 0 ? (p.spent / p.budget) * 100 : 0;
                return (
                  <div
                    id={`project-card-${p.id}`}
                    key={p.id}
                    onClick={() => setSelectedProjectId(p.id)}
                    className="group bg-white border border-zinc-200 rounded-2xl p-6 hover:shadow-md transition-all flex flex-col justify-between h-64 cursor-pointer"
                  >
                    <div>
                      <div className="flex justify-between items-start">
                        <div className="space-y-0.5">
                          <span className="font-mono text-[9px] text-zinc-400 uppercase font-bold tracking-wider">{p.code}</span>
                          <h3 className="font-sans font-bold text-base text-zinc-905 group-hover:text-zinc-950 transition-colors leading-tight">
                            {p.name}
                          </h3>
                        </div>
                        {getStatusComponent(p.status)}
                      </div>
                      <p className="font-sans text-xs text-zinc-500 mt-2 line-clamp-2 leading-relaxed">
                        {p.description}
                      </p>
                    </div>

                    <div className="space-y-4">
                      {/* Progressive spent metrics */}
                      <div className="space-y-1">
                        <div className="flex justify-between items-baseline font-mono text-[10px]">
                          <span className="text-zinc-400">Resource Spent / Total Budget</span>
                          <span className="font-semibold text-zinc-850">
                            {formatCurrency(p.spent)} <span className="text-zinc-300">/</span> {formatCurrency(p.budget)}
                          </span>
                        </div>
                        <div className="h-1.5 w-full bg-zinc-100 rounded-full overflow-hidden border border-zinc-200/50">
                          <div className="h-full bg-zinc-900 rounded-full" style={{ width: `${specRatio}%` }} />
                        </div>
                      </div>

                      {/* Info segments */}
                      <div className="flex items-center justify-between border-t border-zinc-100 pt-3 text-[10px] font-mono text-zinc-400">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="h-3 w-3" />
                          <span className="truncate max-w-[150px]">{p.location}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-zinc-500 font-semibold">{p.boqSynced ? 'BOQ SECURE' : 'BOQ UNSYNCED'}</span>
                          {p.subcontractorCount > 0 && (
                            <span>{p.subcontractorCount} subcontractors</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        ) : (
          /* ========================================================================= */
          /* 2. CHOSEN PROJECT DETAILED SPECIFICATION VIEW                             */
          /* ========================================================================= */
          <motion.div
            key="detail"
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className="space-y-6"
          >
            {/* Back to top header */}
            <div className="flex items-center gap-2">
              <button
                id="projects-back-btn"
                onClick={() => setSelectedProjectId(null)}
                className="p-1.5 border border-zinc-200 hover:border-zinc-300 rounded-lg text-zinc-500 hover:text-zinc-900 bg-white transition-all font-sans text-xs font-semibold flex items-center gap-1"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                <span>Back to entities</span>
              </button>
            </div>

            {/* Detail Identity block */}
            <div id="project-detail-identity" className="p-6 bg-white border border-zinc-200 rounded-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shadow-2xs">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[9px] font-bold tracking-wider text-zinc-400 bg-zinc-100 px-1.5 py-0.5 rounded">
                    {activeDetailProject?.code}
                  </span>
                  {activeDetailProject && getStatusComponent(activeDetailProject.status)}
                </div>
                <h3 className="font-sans font-bold text-2xl text-zinc-900 tracking-tight leading-none">
                  {activeDetailProject?.name}
                </h3>
                <div className="flex items-center gap-4 font-mono text-[11px] text-zinc-400">
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" /> {activeDetailProject?.location}
                  </span>
                  <span>•</span>
                  <span>Supervisor: {activeDetailProject?.owner}</span>
                </div>
              </div>

              {/* Core quick syncing triggers */}
              <div className="flex items-center gap-2 self-stretch md:self-auto justify-between border-t md:border-t-0 border-zinc-100 pt-3 md:pt-0">
                <div className="text-left md:text-right font-mono text-xs">
                  <span className="text-zinc-400 block tracking-wider uppercase text-[9px]">BOQ ERP Sync</span>
                  {activeDetailProject?.boqSynced ? (
                    <span className="text-emerald-600 font-semibold flex items-center gap-1 justify-end">
                      <CheckCircle className="h-3.5 w-3.5" /> Synced
                    </span>
                  ) : (
                    <span className="text-amber-500 font-semibold flex items-center gap-1 justify-end">
                      <AlertTriangle className="h-3.5 w-3.5" /> Draft Local Only
                    </span>
                  )}
                </div>
                <button
                  id="sync-boq-drawer-toggle-btn"
                  onClick={() => setIsSyncDrawerOpen(true)}
                  className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 text-white font-medium text-xs rounded-xl flex items-center gap-1.5 transition-colors shadow-sm"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>Sync BIM Model</span>
                </button>
              </div>
            </div>

            {/* Narrative / Description */}
            <div className="p-5 bg-zinc-50 border border-zinc-200/60 rounded-xl">
              <span className="font-mono text-[9px] uppercase tracking-wider text-zinc-450 font-bold block mb-1">Contractor Mandate & Scope description</span>
              <p className="font-sans text-xs text-zinc-600 leading-relaxed">
                {activeDetailProject?.description}
              </p>
            </div>

            {/* Active BOQ Ledger Items Table */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <h4 className="font-sans font-bold text-sm text-zinc-905 tracking-tight">Bill of Quantities (BOQ) Ledger</h4>
                {activeDetailProject?.boqLastSync && (
                  <span className="font-mono text-[10px] text-zinc-400">
                    Last model sync: <strong className="font-medium text-zinc-600">{activeDetailProject.boqLastSync}</strong>
                  </span>
                )}
              </div>

              <div id="boq-items-table" className="bg-white border border-zinc-200 rounded-2xl overflow-hidden shadow-2xs">
                {activeDetailProject?.boqItems.length === 0 ? (
                  /* Project empty state representation */
                  <div className="p-16 text-center space-y-4">
                    <div className="h-10 w-10 bg-zinc-100 rounded-lg flex items-center justify-center mx-auto text-zinc-400 border border-zinc-150">
                      <Database className="h-5 w-5" />
                    </div>
                    <div>
                      <h5 className="font-sans font-bold text-xs text-zinc-900">No BOQ parameters mapped</h5>
                      <p className="font-sans text-[11px] text-zinc-500 mt-1 max-w-[320px] mx-auto">
                        This entity has not synchronized bill records with Autodesk Revit. Run BIM sync now to populate quantities.
                      </p>
                    </div>
                    <button
                      id="empty-state-sync-boq-btn"
                      onClick={() => setIsSyncDrawerOpen(true)}
                      className="px-4 py-2 bg-zinc-900 text-white hover:bg-zinc-800 font-semibold text-xs rounded-lg transition-colors shadow-2xs inline-flex items-center gap-1.5"
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                      <span>Synchronize with Revit</span>
                    </button>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-xs font-sans">
                      <thead>
                        <tr className="bg-zinc-50 border-b border-zinc-150 font-mono text-[10px] uppercase text-zinc-450 font-semibold">
                          <th className="p-4">Item Code</th>
                          <th className="p-4">Material Specification</th>
                          <th className="p-4">Unit</th>
                          <th className="p-4 text-right">Quantity</th>
                          <th className="p-4 text-right">Unit Rate</th>
                          <th className="p-4 text-right">Total sum</th>
                          <th className="p-4 text-center">Master State</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-zinc-100">
                        {activeDetailProject?.boqItems.map((item) => (
                          <tr id={`boq-item-row-${item.id}`} key={item.id} className="hover:bg-zinc-50/20">
                            <td className="p-4 font-mono font-medium text-zinc-450">{item.itemCode}</td>
                            <td className="p-4 font-sans font-semibold text-zinc-900">{item.description}</td>
                            <td className="p-4 font-mono text-zinc-500">{item.unit}</td>
                            <td className="p-4 font-mono text-right text-zinc-700">{item.quantity.toLocaleString()}</td>
                            <td className="p-4 font-mono text-right text-zinc-700">${item.rate.toLocaleString()}</td>
                            <td className="p-4 font-sans font-bold text-right text-zinc-950">${item.amount.toLocaleString()}</td>
                            <td className="p-4 text-center">
                              {item.status === 'synced' ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[9px] uppercase font-semibold text-emerald-600 bg-emerald-50 border border-emerald-100">
                                  Synced
                                </span>
                              ) : item.status === 'modified' ? (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[9px] uppercase font-semibold text-amber-600 bg-amber-50 border border-amber-100">
                                  Modified
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-mono text-[9px] uppercase font-semibold text-blue-650 bg-blue-50 border border-blue-100 animate-pulse">
                                  Pending Sync
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ========================================================================= */
      /* 3. SYNC BOQ DRAWER SLIDE-OUT (FROM RIGHT)                                  */
      /* ========================================================================= */}
      <AnimatePresence>
        {isSyncDrawerOpen && activeDetailProject && (
          <div id="sync-boq-drawer-overlay" className="fixed inset-0 bg-zinc-950/40 z-50 flex justify-end">
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 220 }}
              className="w-full max-w-md bg-white h-full border-l border-zinc-200 shadow-2xl flex flex-col justify-between"
            >
              {/* Header */}
              <div className="p-6 border-b border-zinc-200 flex justify-between items-center bg-zinc-50">
                <div className="flex items-center gap-2">
                  <Database className="h-4.5 w-4.5 text-zinc-700" />
                  <div>
                    <h3 className="font-sans font-bold text-sm text-zinc-900 leading-none">BIM Model Integrator</h3>
                    <p className="font-mono text-[10px] text-zinc-400 mt-0.5 truncate max-w-[200px]">{activeDetailProject.name}</p>
                  </div>
                </div>
                <button
                  id="close-sync-drawer-btn"
                  onClick={() => setIsSyncDrawerOpen(false)}
                  className="p-1 px-2 border border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-500 rounded-lg text-xs font-mono transition-colors"
                >
                  ✕ CLOSE
                </button>
              </div>

              {/* Drawer central log / trigger console */}
              <div className="p-6 overflow-y-auto space-y-6 flex-1">
                <div className="p-4 bg-zinc-900 text-zinc-200 rounded-2xl font-mono text-xs space-y-3 leading-relaxed shadow-inner">
                  <div className="flex justify-between items-center text-zinc-455 border-b border-zinc-800 pb-2">
                    <span>REVIT DATA FEED</span>
                    <span className="text-[10px] text-zinc-500">Node: 3000-Sync</span>
                  </div>
                  
                  {syncLogs.length === 0 ? (
                    <div id="feed-idle" className="text-zinc-500 py-4 italic">
                      Systems listening. Ready for BIM core synchronization pipeline.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {syncLogs.map((log, lIdx) => (
                        <div key={lIdx} className="flex gap-2">
                          <span className="text-[#34d399] select-none">&gt;</span>
                          <span>{log}</span>
                        </div>
                      ))}
                      {isSyncing && (
                        <div className="flex items-center gap-2 text-zinc-450 italic mt-2 animate-pulse">
                          <RefreshCw className="h-3.5 w-3.5 animate-spin text-[#34d399]" />
                          <span>Revit compiler compiling calculations...</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Scope selection parameters */}
                <div className="space-y-4">
                  <span className="font-mono text-[9px] uppercase tracking-wider text-zinc-450 font-bold block">Target ERP Environment</span>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 border border-zinc-900 rounded-xl bg-zinc-50 flex items-center gap-2 justify-center cursor-pointer">
                      <Building className="h-4 w-4 text-zinc-800" />
                      <span className="text-xs font-bold text-zinc-900 font-sans">Autodesk BIM 360</span>
                    </div>
                    <div className="p-3 border border-zinc-250 rounded-xl hover:border-zinc-400 flex items-center gap-2 justify-center cursor-pointer transition-colors opacity-60">
                      <FileSpreadsheet className="h-4 w-4 text-zinc-500" />
                      <span className="text-xs font-semibold text-zinc-600 font-sans">Raw Ledger Sheet</span>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-zinc-650 leading-relaxed space-y-2">
                  <p className="font-semibold text-zinc-850">Regulatory Notice:</p>
                  <p>
                    Running synchronization will overwrite current local draft BOQ item quantities in favor of BIM engineering metrics. Proceed with program authorization guidelines.
                  </p>
                </div>
              </div>

              {/* Sync Actions Footer */}
              <div className="p-6 border-t border-zinc-200 bg-zinc-50">
                <button
                  id="run-erp-sync-btn"
                  onClick={triggerBOQSync}
                  disabled={isSyncing}
                  className="w-full py-3 bg-zinc-900 text-white font-bold text-xs rounded-xl hover:bg-zinc-805 transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
                >
                  {isSyncing ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      <span>Transmitting Ledger Node...</span>
                    </>
                  ) : (
                    <>
                      <HardDriveUpload className="h-4 w-4" />
                      <span>Initiate Master CAD Sync</span>
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ========================================================================= */
      /* 4. NEW PROJECT REGISTRATION DIALOG / MODAL                                 */
      /* ========================================================================= */}
      <AnimatePresence>
        {isNewProjectModalOpen && (
          <div id="new-project-modal-overlay" className="fixed inset-0 bg-zinc-900/50 flex justify-center items-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="w-full max-w-md bg-white rounded-3xl overflow-hidden border border-zinc-200 shadow-2xl flex flex-col"
            >
              {/* Form container */}
              <form onSubmit={handleCreateProjectSubmit} className="flex flex-col h-full">
                <div className="p-6 border-b border-zinc-230 bg-zinc-50 flex justify-between items-start">
                  <div>
                    <h3 className="font-sans font-bold text-base text-zinc-900 tracking-tight">Initialize Infrastructure Unit</h3>
                    <p className="font-mono text-[10px] text-zinc-500 mt-0.5">Register a new physical development program unit</p>
                  </div>
                  <button
                    id="close-new-project-modal-top"
                    type="button"
                    onClick={() => setIsNewProjectModalOpen(false)}
                    className="p-1 hover:bg-zinc-200 rounded-lg text-zinc-400 hover:text-zinc-700 transition-colors font-mono text-xs font-semibold"
                  >
                    ✕
                  </button>
                </div>

                <div className="p-6 space-y-4">
                  {/* Name field */}
                  <div className="space-y-1">
                    <label className="font-sans text-xs font-semibold text-zinc-700 block">Development Name:</label>
                    <input
                      id="input-project-name"
                      type="text"
                      required
                      placeholder="e.g. Grand Residence Phase 1"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      className="w-full text-xs font-sans p-2.5 border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 bg-zinc-50 hover:border-zinc-300 focus:bg-white transition-all shadow-2xs"
                    />
                  </div>

                  {/* Code & Budget row */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="font-sans text-xs font-semibold text-zinc-700 block">Program Code:</label>
                      <input
                        id="input-project-code"
                        type="text"
                        required
                        placeholder="PRJ-001-E"
                        value={newCode}
                        onChange={(e) => setNewCode(e.target.value)}
                        className="w-full text-xs font-mono p-2.5 border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 bg-zinc-50 hover:border-zinc-300 focus:bg-white transition-all shadow-2xs"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="font-sans text-xs font-semibold text-zinc-700 block">Initial Budget ($):</label>
                      <input
                        id="input-project-budget"
                        type="number"
                        required
                        placeholder="18000000"
                        value={newBudget}
                        onChange={(e) => setNewBudget(e.target.value)}
                        className="w-full text-xs font-mono p-2.5 border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 bg-zinc-50 hover:border-zinc-300 focus:bg-white transition-all shadow-2xs"
                      />
                    </div>
                  </div>

                  {/* Loc & Leader row */}
                  <div className="space-y-1">
                    <label className="font-sans text-xs font-semibold text-zinc-700 block">Operational Site Location:</label>
                    <input
                      id="input-project-location"
                      type="text"
                      placeholder="e.g. Hillside District, Sector 12"
                      value={newLocation}
                      onChange={(e) => setNewLocation(e.target.value)}
                      className="w-full text-xs font-sans p-2.5 border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 bg-zinc-50 hover:border-zinc-300 focus:bg-white transition-all shadow-2xs"
                    />
                  </div>

                  {/* Leader */}
                  <input type="hidden" value={newOwner} />

                  {/* Summary / Memo */}
                  <div className="space-y-1">
                    <label className="font-sans text-xs font-semibold text-zinc-700 block">Scope Brief & Specifications:</label>
                    <textarea
                      id="input-project-description"
                      placeholder="Specify core physical targets, LEED classifications, or subcontractor schedules..."
                      value={newDescription}
                      onChange={(e) => setNewDescription(e.target.value)}
                      className="w-full text-xs font-sans p-2.5 border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 bg-zinc-50 hover:border-zinc-300 focus:bg-white transition-all shadow-2xs"
                      rows={3}
                    />
                  </div>
                </div>

                <div className="p-6 border-t border-zinc-200 bg-zinc-50 flex gap-3">
                  <button
                    id="new-project-cancel-btn"
                    type="button"
                    onClick={() => setIsNewProjectModalOpen(false)}
                    className="flex-1 py-2.5 border border-zinc-200 bg-white hover:bg-zinc-100 text-zinc-700 font-semibold rounded-xl text-xs transition-colors"
                  >
                    Cancel Draft
                  </button>
                  <button
                    id="new-project-submit-btn"
                    type="submit"
                    className="flex-1 py-2.5 bg-zinc-900 text-white hover:bg-zinc-800 font-semibold rounded-xl text-xs transition-colors shadow-sm"
                  >
                    Register Entity
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
