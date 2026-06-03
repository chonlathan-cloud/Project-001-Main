import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Search, 
  Bell, 
  HelpCircle, 
  Plus, 
  SlidersHorizontal, 
  MoreVertical, 
  ChevronLeft, 
  ChevronRight, 
  Building, 
  RefreshCw, 
  AlertTriangle, 
  FileText, 
  FileSpreadsheet, 
  Database, 
  HardDriveUpload, 
  X, 
  Check, 
  CheckCircle 
} from 'lucide-react';
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
  // Initialize with the first project selected
  const [selectedProjectId, setSelectedProjectId] = useState<string>(projects[0]?.id || 'PRJ-001');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'list' | 'detail'>('list');
  const [isSyncDrawerOpen, setIsSyncDrawerOpen] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncLogs, setSyncLogs] = useState<string[]>([]);
  
  // Create Project modal fields
  const [newName, setNewName] = useState('');
  const [newCode, setNewCode] = useState('PRJ-24-080');
  const [newBudget, setNewBudget] = useState('15000000');
  const [newLocation, setNewLocation] = useState('East Industrial Sector');
  const [newDescription, setNewDescription] = useState('');

  // Find currently selected project details
  const activeProject = projects.find((p) => p.id === selectedProjectId) || projects[0];

  // Filtered projects based on search query
  const filteredProjects = projects.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.location.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Formatting helpers
  const formatCurrency = (val: number) => {
    return `$${val.toLocaleString()}`;
  };

  const getStatusBadge = (status: ProjectStatus) => {
    switch (status) {
      case 'active':
        return (
          <span className="inline-block font-sans text-[10px] font-extrabold text-[#2E7D32] bg-[#E8F5E9] px-2.5 py-0.5 rounded-full tracking-wide uppercase">
            ACTIVE
          </span>
        );
      case 'draft':
        return (
          <span className="inline-block font-sans text-[10px] font-extrabold text-[#8F6B00] bg-[#FFF8E1] px-2.5 py-0.5 rounded-full tracking-wide uppercase">
            PENDING
          </span>
        );
      case 'on_hold':
        return (
          <span className="inline-block font-sans text-[10px] font-extrabold text-[#C5221F] bg-[#FCE8E6] px-2.5 py-0.5 rounded-full tracking-wide uppercase">
            DELAYED
          </span>
        );
      case 'completed':
        return (
          <span className="inline-block font-sans text-[10px] font-extrabold text-[#1E3A8A] bg-[#DBEAFE] px-2.5 py-0.5 rounded-full tracking-wide uppercase">
            COMPLETED
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
      budget: parseFloat(newBudget) || 5000000,
      spent: 0,
      progress: 0,
      owner: 'James Harrison',
      subcontractorCount: 0,
      startDate: new Date().toISOString().split('T')[0],
      endDate: '2028-12-30',
      description: newDescription || 'Standard development initialized under parent Projects-001.',
      boqSynced: false,
      location: newLocation,
      boqItems: [],
    };

    onAddProject(newProj);
    setIsNewProjectModalOpen(false);

    // Reset fields
    setNewName('');
    setNewCode(`PRJ-24-${Math.floor(100 + Math.random() * 900)}`);
    setNewBudget('12000000');
    setNewDescription('');
  };

  // Run Autodesk/Spreadsheet synchronization simulation
  const triggerBOQSync = () => {
    if (!activeProject) return;
    setIsSyncing(true);
    setSyncLogs(['Establishing connection to Autodesk BIM 360...', 'Querying Revit Structural Quantities module...']);

    setTimeout(() => {
      setSyncLogs((prev) => [...prev, 'Comparing 1,248 database nodes against current BOQ...']);
    }, 1000);

    setTimeout(() => {
      setSyncLogs((prev) => [...prev, 'Updating unit amounts & generating ledger variance logs...']);
    }, 2000);

    setTimeout(() => {
      const updatedBOQ: BOQItem[] = activeProject.boqItems.length === 0 ? [
        { id: 'boq-sync-1', itemCode: '03.2000', description: 'Simulated Synced Foundation Steel Base Rebar', unit: 'ton', quantity: 180, rate: 1950, amount: 351000, status: 'synced' },
        { id: 'boq-sync-2', itemCode: '04.2200', description: 'Concrete masonry blocks (200mm thick)', unit: 'm2', quantity: 4500, rate: 65, amount: 292500, status: 'synced' }
      ] : activeProject.boqItems.map(item => ({ ...item, status: 'synced' }));

      const currentTimestamp = new Date().toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
        hour12: true
      });

      const updatedProj: Project = {
        ...activeProject,
        boqSynced: true,
        boqLastSync: `${currentTimestamp}`,
        boqItems: updatedBOQ
      };

      onUpdateProject(updatedProj);
      onAddActivity(
        `Synchronized ${updatedBOQ.length} structural lines in BOQ with Revit BIM 360 master`,
        updatedProj.code,
        updatedProj.name,
        'sync'
      );

      setIsSyncing(false);
      setIsSyncDrawerOpen(false);
    }, 3500);
  };

  // Details mappings for visual replica of the side widgets
  const getProjectMetadata = (proj: Project) => {
    if (proj.code === 'PRJ-24-001') {
      return { value: '$12,450,000', items: '1,248', mapped: '98% mapped', file: 'Master_BOQ_v2.xlsx', unmapped: '12', variations: '3' };
    } else if (proj.code === 'PRJ-24-042') {
      return { value: '$8,100,000', items: '0', mapped: '0% mapped', file: 'Master_BOQ_draft.xlsx', unmapped: '0', variations: '0' };
    } else if (proj.code === 'PRJ-23-118') {
      return { value: '$22,000,000', items: '842', mapped: '85% mapped', file: 'Logistics_BOQ_v1.xlsx', unmapped: '4', variations: '1' };
    }
    // Fallbacks
    return { 
      value: formatCurrency(proj.budget), 
      items: proj.boqItems.length > 0 ? proj.boqItems.length.toString() : '0', 
      mapped: proj.boqSynced ? '100% mapped' : '0% mapped',
      file: proj.boqSynced ? 'Master_BOQ_v1.xlsx' : 'No BOQ mapped',
      unmapped: proj.boqSynced ? '0' : '8',
      variations: '0'
    };
  };

  const meta = getProjectMetadata(activeProject);

  return (
    <div id="projects-view" className="space-y-6">
      {/* 1. TOP HEADER SECTION */}
      <div className="flex flex-col md:flex-row justify-between items-stretch md:items-center gap-4">
        {/* Search Input Bar */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-[15px] w-[15px] text-zinc-400" />
          <input
            type="text"
            placeholder="Search projects, BOQs, items..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-zinc-200 rounded-lg text-sm bg-white focus:outline-none focus:border-zinc-300 focus:ring-1 focus:ring-zinc-300 transition-all font-sans placeholder-zinc-400 font-medium"
          />
        </div>

        {/* Action icons & User picture */}
        <div className="flex items-center justify-end gap-5">
          <button className="relative p-1 text-zinc-700 hover:text-zinc-950 transition-colors cursor-pointer">
            <Bell className="h-[21px] w-[21px] stroke-[1.75px]" />
            <span className="absolute top-[2px] right-[2px] h-2 w-2 rounded-full bg-red-600 border border-white" />
          </button>
          <button className="p-1 text-zinc-700 hover:text-zinc-950 transition-colors cursor-pointer">
            <HelpCircle className="h-[21px] w-[21px] stroke-[1.75px]" />
          </button>
          <img
            src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=100&h=100&q=80"
            alt="Profile picture"
            className="h-8 w-8 rounded-full border border-zinc-200 object-cover shadow-2xs cursor-pointer"
          />
        </div>
      </div>

      {/* View Mode Switching */}
      {viewMode === 'list' ? (
        <>
          {/* 2. PAGE HEADER TITLE */}
          <div className="border-t border-zinc-200/40 pt-5">
            <h2 className="font-sans font-bold text-[31px] text-zinc-900 leading-tight tracking-tight">
              Projects
            </h2>
            <p className="font-sans text-[13px] text-zinc-500 font-medium mt-0.5">
              Manage active construction sites, budgets, and BOQ synchronizations.
            </p>
          </div>

          {/* 3. CORE SPLIT GRID LAYOUT */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 pt-1 items-start">
            
            {/* Left Master Section: Active Projects Table (Width 3/5) */}
            <div className="lg:col-span-3 bg-white border border-zinc-200/80 rounded-2xl p-5 shadow-2xs flex flex-col justify-between">
              <div>
                {/* Table Header Row */}
                <div className="flex justify-between items-center mb-5">
                  <h3 className="font-sans font-bold text-base text-zinc-900 tracking-tight">
                    Active Projects
                  </h3>
                  <div className="flex items-center gap-3 text-zinc-400">
                    <button className="p-1.5 hover:bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-600 cursor-pointer shadow-3xs">
                      <SlidersHorizontal className="h-4 w-4 stroke-[2px]" />
                    </button>
                    <button className="p-1.5 hover:bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-600 cursor-pointer shadow-3xs">
                      <MoreVertical className="h-4 w-4 stroke-[2px]" />
                    </button>
                  </div>
                </div>

                {/* Master Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-zinc-150 font-sans font-extrabold text-[11px] text-zinc-400 tracking-wider uppercase">
                        <th className="py-2.5 w-5/12 pl-2">Project Code</th>
                        <th className="py-2.5 w-3/12">Location</th>
                        <th className="py-2.5 w-2/12">Status</th>
                        <th className="py-2.5 w-2/12">Budget</th>
                        <th className="py-2.5 w-2/12 text-right pr-2">Progress</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-50">
                      {filteredProjects.map((p) => {
                        const isSelected = selectedProjectId === p.id;
                        let progressColor = 'bg-[#3F5E53]'; // Active green
                        if (p.status === 'draft') progressColor = 'bg-[#A88B60]'; // Pending Gold/Tan
                        if (p.status === 'on_hold') progressColor = 'bg-[#C5221F]'; // Delayed Red

                        return (
                          <tr 
                            id={`project-table-row-${p.id}`}
                            key={p.id}
                            onClick={() => setSelectedProjectId(p.id)}
                            onDoubleClick={() => {
                              setSelectedProjectId(p.id);
                              setViewMode('detail');
                            }}
                            className={`hover:bg-zinc-50/50 cursor-pointer transition-colors group ${
                              isSelected ? 'bg-zinc-50/30' : ''
                            }`}
                          >
                            {/* Project Code (Selected highlights with forest green left border) */}
                            <td className={`py-3.5 pl-2 font-sans relative ${
                              isSelected ? 'border-l-[3.5px] border-[#3F5E53]' : ''
                            }`}>
                              <div className="font-bold text-[13px] text-zinc-900">{p.code}</div>
                              <div className="text-[11px] font-semibold text-zinc-400">{p.name}</div>
                            </td>

                            {/* Location */}
                            <td className="py-3.5 font-sans font-semibold text-[13px] text-zinc-700">
                              {p.location}
                            </td>

                            {/* Status badge */}
                            <td className="py-3.5">
                              {getStatusBadge(p.status)}
                            </td>

                            {/* Budget */}
                            <td className="py-3.5 font-sans font-bold text-[13px] text-zinc-800">
                              {p.budget >= 1000000 ? `$${(p.budget / 1000000).toFixed(1)}M` : formatCurrency(p.budget)}
                            </td>

                            {/* Progress and mini progress-bar */}
                            <td className="py-3.5 text-right pr-2 font-sans">
                              <div className="flex items-center justify-end gap-2">
                                <div className="w-[45px] h-1.5 bg-zinc-100 rounded-full overflow-hidden border border-zinc-200/50">
                                  <div className={`h-full ${progressColor} rounded-full`} style={{ width: `${p.progress}%` }} />
                                </div>
                                <span className="font-extrabold text-[12px] text-zinc-800 w-[26px]">
                                  {p.progress}%
                                </span>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Table Footer with pagination indicator */}
              <div className="flex justify-between items-center border-t border-zinc-100 pt-4 mt-6 text-zinc-400 font-sans text-xs">
                <span className="font-semibold text-zinc-450">
                  Showing 1-{filteredProjects.length} of {projects.length} projects
                </span>
                <div className="flex items-center gap-1.5">
                  <button className="p-1 border border-zinc-200 hover:border-zinc-300 rounded-md text-zinc-550 cursor-pointer shadow-3xs">
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                  <button className="p-1 border border-zinc-200 hover:border-zinc-300 rounded-md text-zinc-550 cursor-pointer shadow-3xs">
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            {/* Right Detail Section: Selected Project Details Panel & Variations (Width 2/5) */}
            <div className="lg:col-span-2 space-y-4">
              
              {/* Main Selected Project Info Card */}
              {activeProject && (
                <div className="bg-white border border-zinc-200/80 rounded-2xl p-5 shadow-2xs space-y-5">
                  
                  {/* Identity Row */}
                  <div className="flex items-center gap-3 cursor-pointer group" onClick={() => setViewMode('detail')} title="Double click table row or click here for full dashboard">
                    <div className="h-10 w-10 bg-[#E8F5E9] rounded-xl flex items-center justify-center text-[#3F5E53] shadow-3xs group-hover:bg-[#3F5E53] group-hover:text-white transition-colors">
                      <Building className="h-5 w-5 stroke-[2px]" />
                    </div>
                    <div>
                      <h4 className="font-sans font-extrabold text-base text-zinc-900 leading-tight group-hover:text-[#3F5E53] transition-colors">
                        {activeProject.code}
                      </h4>
                      <p className="font-sans text-[12px] font-semibold text-zinc-400">
                        {activeProject.name}
                      </p>
                    </div>
                  </div>

                  <div className="border-t border-zinc-100" />

                  {/* Metrics Summary Row */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="font-sans text-[10px] font-bold text-zinc-400 uppercase tracking-wider block">
                        Contract Value
                      </span>
                      <span className="font-sans font-extrabold text-[17px] text-zinc-900 block mt-1 tracking-tight">
                        {meta.value}
                      </span>
                    </div>
                    <div>
                      <span className="font-sans text-[10px] font-bold text-zinc-400 uppercase tracking-wider block">
                        BOQ Items
                      </span>
                      <span className="font-sans font-extrabold text-[17px] text-zinc-900 block mt-1 tracking-tight flex items-baseline gap-1">
                        {activeProject.boqItems.length.toLocaleString()} 
                        {activeProject.boqSynced && (
                          <span className="text-[10px] font-semibold text-zinc-400 tracking-normal">
                            (98% mapped)
                          </span>
                        )}
                        {!activeProject.boqSynced && (
                          <span className="text-[10px] font-semibold text-zinc-400 tracking-normal">
                            (0% mapped)
                          </span>
                        )}
                      </span>
                    </div>
                  </div>

                  <div className="border-t border-zinc-100" />

                  {/* BOQ Management block */}
                  <div className="space-y-3 pt-0.5">
                    <span className="font-sans text-[11px] font-bold text-zinc-400 tracking-wider block uppercase">
                      BOQ Management
                    </span>

                    {/* Spreadsheet document box */}
                    <div className="p-3 bg-zinc-50 border border-zinc-200/60 rounded-xl flex items-center justify-between shadow-3xs">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <FileText className="h-5 w-5 text-zinc-400 flex-shrink-0" />
                        <div className="min-w-0">
                          <span className="font-sans font-bold text-[13px] text-zinc-800 block truncate">
                            {meta.file}
                          </span>
                        </div>
                      </div>
                      {activeProject.boqSynced && (
                        <span className="font-sans text-[10px] font-semibold text-zinc-400 whitespace-nowrap">
                          Updated 2h ago
                        </span>
                      )}
                    </div>

                    {/* Synchronize active model outline action button */}
                    <button
                      id="sync-boq-action-btn"
                      onClick={() => setIsSyncDrawerOpen(true)}
                      className="w-full py-2.5 text-center text-[12px] font-bold text-[#8C7047] border border-[#EBE4D8] hover:bg-[#FAF7F2] active:scale-[0.99] rounded-lg tracking-wider transition-all uppercase flex items-center justify-center gap-2 cursor-pointer mt-1"
                    >
                      <RefreshCw className="h-4 w-4 stroke-[2px]" />
                      <span>Sync BOQ</span>
                    </button>
                  </div>

                </div>
              )}

              {/* Dual Small Side-by-Side Cards (Unmapped and Variations) */}
              <div className="grid grid-cols-2 gap-4">
                {/* Card 1: Unmapped Items */}
                <div className="bg-white border border-zinc-200/80 rounded-2xl p-4 shadow-2xs flex flex-col gap-2.5">
                  <AlertTriangle className="h-5 w-5 text-zinc-400 stroke-[2px]" />
                  <div>
                    <span className="font-sans font-extrabold text-[23px] text-zinc-900 leading-none block">
                      {meta.unmapped}
                    </span>
                    <span className="font-sans text-[11px] font-semibold text-zinc-400 block mt-1 leading-tight">
                      Unmapped Items
                    </span>
                  </div>
                </div>

                {/* Card 2: Pending Variations */}
                <div className="bg-white border border-zinc-200/80 rounded-2xl p-4 shadow-2xs flex flex-col gap-2.5">
                  <svg 
                    xmlns="http://www.w3.org/2000/svg" 
                    viewBox="0 0 24 24" 
                    fill="none" 
                    stroke="currentColor" 
                    strokeWidth="2" 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    className="h-5 w-5 text-zinc-400 stroke-[2px]"
                  >
                    <rect width="20" height="14" x="2" y="5" rx="2" />
                    <line x1="2" x2="22" y1="10" y2="10" />
                    <path d="M12 14h.01M16 14h.01M8 14h.01" />
                  </svg>
                  <div>
                    <span className="font-sans font-extrabold text-[23px] text-zinc-900 leading-none block">
                      {meta.variations}
                    </span>
                    <span className="font-sans text-[11px] font-semibold text-zinc-400 block mt-1 leading-tight">
                      Pending Variations
                    </span>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </>
      ) : activeProject && activeProject.boqItems.length === 0 ? (
        <div className="pt-2">
          {/* Breadcrumbs */}
          <div className="flex items-center gap-2 text-[13px] font-semibold text-zinc-500 mb-6">
            <button onClick={() => setViewMode('list')} className="hover:text-zinc-900 transition-colors cursor-pointer">Projects</button>
            <ChevronRight className="h-3.5 w-3.5 stroke-[3px]" />
            <span className="text-zinc-900">{activeProject.code}</span>
          </div>

          {/* Empty State Header */}
          <div className="flex justify-between items-end mb-6 pb-2 border-b border-zinc-200/50">
             <div>
                <div className="flex items-center gap-3 mb-2">
                   <span className="px-2 py-0.5 bg-[#F5E6CC] text-[#A88B60] text-[10px] font-bold uppercase rounded-md tracking-wider">NEW PROJECT</span>
                   <span className="text-[11px] text-zinc-500 font-medium">Created today</span>
                </div>
                <h2 className="font-sans font-bold text-[28px] text-zinc-900 tracking-tight">{activeProject.name}</h2>
             </div>
             <button className="px-4 py-2 bg-white border border-[#A88B60] text-[#A88B60] text-[11px] font-bold rounded-lg hover:bg-[#FAF7F2] transition-colors cursor-pointer mb-1 shadow-sm">
               Project Settings
             </button>
          </div>

          {/* Empty State Card */}
          <div className="bg-white border border-zinc-200/80 rounded-2xl shadow-sm flex flex-col items-center justify-center p-16 min-h-[550px] mt-8">
             <img src="/empty_boq.png" alt="No BOQ Illustration" className="w-56 h-56 object-contain mb-8 mix-blend-multiply" />
             <h3 className="font-sans font-bold text-[22px] text-zinc-900 mb-3">No Bill of Quantities Found</h3>
             <p className="font-sans text-[13px] text-zinc-500 text-center max-w-[420px] mb-8 leading-relaxed">
               Start tracking materials, costs, and labor for {activeProject.name}. Sync your existing BOQ to populate the tracker instantly.
             </p>
             <button
               onClick={() => setIsSyncDrawerOpen(true)}
               className="px-6 py-3 bg-[#597869] text-white hover:bg-[#486457] text-[12px] font-bold rounded-lg transition-colors flex items-center gap-2.5 shadow-sm mb-7 cursor-pointer"
             >
               <RefreshCw className="h-4 w-4 stroke-[2px]" />
               Sync BOQ from Google Sheets
             </button>
             <div className="flex items-center justify-center w-full max-w-[280px] mb-6 relative">
               <div className="absolute inset-0 flex items-center">
                 <div className="w-full border-t border-zinc-200"></div>
               </div>
               <div className="relative flex justify-center text-[10px] px-3 bg-white text-zinc-400 font-semibold lowercase">
                 or
               </div>
             </div>
             <div className="flex gap-8 text-[11px] font-bold text-zinc-600">
               <button className="hover:text-zinc-900 transition-colors cursor-pointer">Upload CSV</button>
               <button className="hover:text-zinc-900 transition-colors cursor-pointer">Create Manually</button>
             </div>
          </div>
        </div>
      ) : activeProject ? (
        <div className="pt-2">
          {/* Breadcrumbs */}
          <div className="flex items-center gap-2 text-[13px] font-semibold text-zinc-500 mb-6">
            <button onClick={() => setViewMode('list')} className="hover:text-zinc-900 transition-colors cursor-pointer">Projects</button>
            <ChevronRight className="h-3.5 w-3.5 stroke-[3px]" />
            <span className="text-zinc-900">{activeProject.code}</span>
          </div>

          {/* Dashboard Header */}
          <div className="flex justify-between items-start mb-8 pb-5 border-b border-zinc-200/60">
             <div>
                <div className="flex items-center gap-3 mb-1">
                   <h2 className="font-sans font-extrabold text-[32px] text-zinc-900 tracking-tight leading-none">{activeProject.name}</h2>
                   <div className="mt-1">{getStatusBadge(activeProject.status)}</div>
                </div>
                <p className="text-[13px] text-zinc-600 font-medium">{activeProject.location}</p>
             </div>
             <div className="flex items-center gap-3">
               <button className="px-4 py-2 bg-white border border-[#A88B60] text-[#A88B60] text-[12px] font-bold rounded-lg hover:bg-[#FAF7F2] transition-colors flex items-center gap-2 cursor-pointer shadow-sm">
                 <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
                 Edit Project
               </button>
               <button className="px-4 py-2 bg-white border border-[#A88B60] text-[#A88B60] text-[12px] font-bold rounded-lg hover:bg-[#FAF7F2] transition-colors flex items-center gap-2 cursor-pointer shadow-sm">
                 <FileText className="w-4 h-4" />
                 Generate Report
               </button>
               <button
                 onClick={() => setIsSyncDrawerOpen(true)}
                 className="px-4 py-2 bg-[#597869] text-white hover:bg-[#486457] text-[12px] font-bold rounded-lg transition-colors flex items-center gap-2 shadow-sm cursor-pointer"
               >
                 <RefreshCw className="h-4 w-4" />
                 Sync BOQ
               </button>
             </div>
          </div>

          {/* 4 Summary Cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
             {/* Total Budget */}
             <div className="bg-white border border-zinc-200/80 rounded-2xl p-6 shadow-2xs">
               <div className="text-[11px] font-bold text-zinc-500 tracking-wider uppercase mb-1">Total Budget</div>
               <div className="text-[28px] font-extrabold text-zinc-900 tracking-tight">${(activeProject.budget / 1000000).toFixed(1)}M</div>
             </div>
             
             {/* Spent To Date */}
             <div className="bg-white border border-zinc-200/80 rounded-2xl p-6 shadow-2xs flex flex-col justify-between">
               <div>
                 <div className="text-[11px] font-bold text-zinc-500 tracking-wider uppercase mb-1">Spent To Date</div>
                 <div className="flex items-end gap-2 mb-3">
                   <div className="text-[28px] font-extrabold text-zinc-900 tracking-tight leading-none">${(activeProject.spent / 1000000).toFixed(1)}M</div>
                   <div className="text-[13px] font-bold text-zinc-500 mb-0.5">{((activeProject.spent / activeProject.budget) * 100).toFixed(1)}%</div>
                 </div>
               </div>
               <div className="w-full h-[5px] bg-zinc-100 rounded-full overflow-hidden border border-zinc-200/50">
                 <div className="h-full bg-[#3F5E53] rounded-full" style={{ width: `${(activeProject.spent / activeProject.budget) * 100}%` }}></div>
               </div>
             </div>

             {/* Remaining */}
             <div className="bg-white border border-zinc-200/80 rounded-2xl p-6 shadow-2xs">
               <div className="text-[11px] font-bold text-zinc-500 tracking-wider uppercase mb-1">Remaining</div>
               <div className="text-[28px] font-extrabold text-zinc-900 tracking-tight">${((activeProject.budget - activeProject.spent) / 1000000).toFixed(1)}M</div>
             </div>

             {/* Completion */}
             <div className="bg-white border border-zinc-200/80 rounded-2xl p-6 shadow-2xs flex justify-between items-center">
               <div>
                 <div className="text-[11px] font-bold text-zinc-500 tracking-wider uppercase mb-1">Completion</div>
                 <div className="text-[28px] font-extrabold text-zinc-900 tracking-tight leading-none mb-1.5">{activeProject.progress}%</div>
                 <div className="text-[11.5px] font-semibold text-zinc-500">On schedule</div>
               </div>
               <div className="h-9 w-9 bg-[#3F5E53] rounded-full flex items-center justify-center shadow-sm">
                 <Check className="h-5 w-5 text-white stroke-[3.5px]" />
               </div>
             </div>
          </div>

          {/* BOQ Comparison */}
          <div className="bg-white border border-zinc-200/80 rounded-2xl p-6 shadow-2xs mb-6">
             <div className="flex justify-between items-center mb-6">
               <h3 className="text-xl font-bold text-zinc-900">BOQ Comparison</h3>
               <div className="flex items-center gap-3 text-zinc-400">
                  <button className="p-1.5 hover:bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-600 cursor-pointer"><SlidersHorizontal className="h-4 w-4" /></button>
                  <button className="p-1.5 hover:bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-600 cursor-pointer"><MoreVertical className="h-4 w-4" /></button>
               </div>
             </div>
             
             <table className="w-full text-left border-collapse">
               <thead>
                 <tr className="border-b border-zinc-200/60 font-bold text-[11px] text-zinc-500 tracking-wider uppercase">
                   <th className="py-3 pb-4 pl-2 w-1/3">Cost Category</th>
                   <th className="py-3 pb-4 text-center">Customer BOQ</th>
                   <th className="py-3 pb-4 text-center">Subcontractor BOQ</th>
                   <th className="py-3 pb-4 text-right">Variance</th>
                   <th className="py-3 pb-4 text-right pr-6">Status</th>
                 </tr>
               </thead>
               <tbody className="divide-y divide-zinc-100">
                 <tr className="group">
                   <td className="py-4 pl-2 font-medium text-[13px] text-zinc-800 flex items-center gap-3">
                     <div className="p-2 bg-zinc-100/80 rounded-lg text-zinc-500"><svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg></div>
                     Material Costs
                   </td>
                   <td className="py-4 text-center font-medium text-[13px] text-zinc-700">$4,250,000</td>
                   <td className="py-4 text-center font-medium text-[13px] text-zinc-700">$4,180,000</td>
                   <td className="py-4 text-right font-bold text-[13px] text-[#3F5E53]">-$70,000</td>
                   <td className="py-4 text-right pr-8"><span className="inline-flex text-[#3F5E53]"><svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M12 5v14M19 12l-7 7-7-7"/></svg></span></td>
                 </tr>
                 <tr className="group">
                   <td className="py-4 pl-2 font-medium text-[13px] text-zinc-800 flex items-center gap-3">
                     <div className="p-2 bg-zinc-100/80 rounded-lg text-zinc-500"><svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg></div>
                     Labor Costs
                   </td>
                   <td className="py-4 text-center font-medium text-[13px] text-zinc-700">$5,800,000</td>
                   <td className="py-4 text-center font-medium text-[13px] text-zinc-700">$6,050,000</td>
                   <td className="py-4 text-right font-bold text-[13px] text-[#C5221F]">+$250,000</td>
                   <td className="py-4 text-right pr-8"><span className="inline-flex text-[#C5221F]"><AlertTriangle className="w-4 h-4 stroke-[2.5px]" /></span></td>
                 </tr>
                 <tr className="group">
                   <td className="py-4 pl-2 font-medium text-[13px] text-zinc-800 flex items-center gap-3">
                     <div className="p-2 bg-zinc-100/80 rounded-lg text-zinc-500"><svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg></div>
                     Equipment Rentals
                   </td>
                   <td className="py-4 text-center font-medium text-[13px] text-zinc-700">$2,350,000</td>
                   <td className="py-4 text-center font-medium text-[13px] text-zinc-700">$2,300,000</td>
                   <td className="py-4 text-right font-bold text-[13px] text-[#3F5E53]">-$50,000</td>
                   <td className="py-4 text-right pr-8"><span className="inline-flex text-[#3F5E53]"><svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M12 5v14M19 12l-7 7-7-7"/></svg></span></td>
                 </tr>
               </tbody>
               <tfoot>
                 <tr className="bg-[#FAF8F6] border-t border-zinc-200">
                   <td className="py-4 pl-4 font-bold text-[12px] text-zinc-900 rounded-l-xl">Total Estimates</td>
                   <td className="py-4 text-center font-bold text-[13px] text-zinc-900">$12,400,000</td>
                   <td className="py-4 text-center font-bold text-[13px] text-zinc-900">$12,530,000</td>
                   <td className="py-4 text-right font-extrabold text-[13px] text-[#C5221F] rounded-r-xl" colSpan={2}>
                     <span className="pr-[4.5rem]">+$130,000</span>
                   </td>
                 </tr>
               </tfoot>
             </table>
          </div>

          {/* Upcoming Milestones */}
          <div className="bg-white border border-zinc-200/80 rounded-2xl p-6 shadow-2xs">
             <h3 className="text-xl font-bold text-zinc-900 mb-7">Upcoming Milestones</h3>
             <div className="relative border-l-2 border-zinc-100 ml-3 space-y-7 pb-2">
                {/* Milestone 1 */}
                <div className="relative pl-6">
                  <div className="absolute w-[11px] h-[11px] bg-[#3F5E53] rounded-full -left-[6.5px] top-1.5 ring-[6px] ring-white" />
                  <div className="flex flex-col gap-1">
                    <span className="font-extrabold text-[14px] text-zinc-900">Foundation Sign-off</span>
                    <span className="text-[12px] font-semibold text-zinc-400 mb-0.5">Oct 15, 2024</span>
                    <p className="text-[13px] text-zinc-700 leading-relaxed max-w-2xl">Final inspection and engineering sign-off for primary sub-structure concrete pour.</p>
                  </div>
                </div>
                {/* Milestone 2 */}
                <div className="relative pl-6">
                  <div className="absolute w-[11px] h-[11px] bg-white border-[2.5px] border-[#3F5E53] rounded-full -left-[6.5px] top-1.5 ring-[6px] ring-white" />
                  <div className="flex flex-col gap-1">
                    <span className="font-extrabold text-[14px] text-zinc-900">Steel Framework Phase 1</span>
                    <span className="text-[12px] font-semibold text-zinc-400 mb-0.5">Nov 02, 2024</span>
                    <p className="text-[13px] text-zinc-700 leading-relaxed max-w-2xl">Commencement of structural steel erection up to level 5.</p>
                  </div>
                </div>
                {/* Milestone 3 */}
                <div className="relative pl-6">
                  <div className="absolute w-[11px] h-[11px] bg-white border-[2.5px] border-zinc-300 rounded-full -left-[6.5px] top-1.5 ring-[6px] ring-white" />
                  <div className="flex flex-col gap-1">
                    <span className="font-extrabold text-[14px] text-zinc-900">HVAC Rough-in</span>
                    <span className="text-[12px] font-semibold text-zinc-400 mb-0.5">Dec 10, 2024</span>
                    <p className="text-[13px] text-zinc-700 leading-relaxed max-w-2xl">Installation of primary mechanical ductwork drops in the podium levels.</p>
                  </div>
                </div>
             </div>
          </div>
        </div>
      ) : null}

      {/* 4. BIM SYNC CONSOLE DRAWER OVERLAY */}
      <AnimatePresence>
        {isSyncDrawerOpen && activeProject && (
          <div id="sync-boq-drawer-overlay" className="fixed inset-0 bg-zinc-900/20 backdrop-blur-sm z-50 flex justify-end">
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 220 }}
              className="w-full max-w-[460px] bg-white h-full border-l border-zinc-200 shadow-2xl flex flex-col justify-between"
            >
              {/* Drawer Header */}
              <div className="p-7 pb-5 border-b border-zinc-150 flex justify-between items-start bg-white">
                <div>
                  <h3 className="font-sans font-bold text-[20px] text-zinc-900 leading-none">Sync BOQ Data</h3>
                  <p className="font-sans text-[12px] text-zinc-500 mt-2">Import line items from Google Sheets</p>
                </div>
                <button
                  id="close-sync-drawer-btn"
                  onClick={() => setIsSyncDrawerOpen(false)}
                  className="p-1.5 hover:bg-zinc-100 text-zinc-500 rounded-md transition-colors cursor-pointer mt-0.5"
                >
                  <X className="h-5 w-5 stroke-[2px]" />
                </button>
              </div>

              {/* Drawer Content */}
              <div className="p-7 overflow-y-auto flex-1 space-y-8">
                
                {/* Step 1 */}
                <div className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="h-6 w-6 shrink-0 rounded-full bg-[#597869] text-white flex items-center justify-center font-bold text-[13px] shadow-sm">1</div>
                    <div className="w-[1.5px] h-full bg-zinc-150 mt-3 -mb-3"></div>
                  </div>
                  <div className="flex-1 pb-3">
                    <h4 className="font-sans font-bold text-[16px] text-zinc-900 mb-3.5">Connect Source</h4>
                    <label className="font-sans text-[10px] font-bold text-zinc-700 tracking-wider uppercase block mb-2">GOOGLE SHEET URL</label>
                    <div className="flex gap-2.5 mb-2.5">
                      <div className="relative flex-1">
                        <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 h-[15px] w-[15px] text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                        </svg>
                        <input
                          type="text"
                          defaultValue="https://docs.google.com/sprea"
                          className="w-full text-[13px] font-sans py-2.5 pl-9 pr-3 border border-zinc-200 rounded-lg focus:outline-none focus:border-[#597869] bg-white transition-all shadow-sm text-zinc-800"
                        />
                      </div>
                      <button className="px-4 bg-[#7A6349] hover:bg-[#68533B] text-white text-[11px] font-bold rounded-lg transition-colors flex items-center gap-1.5 shadow-sm whitespace-nowrap cursor-pointer">
                        <RefreshCw className="h-3 w-3 stroke-[2.5px]" />
                        Load Tabs
                      </button>
                    </div>
                    <div className="flex items-center gap-1.5 text-[#6B7E74] pl-0.5">
                      <CheckCircle className="h-[13px] w-[13px] stroke-[2.5px]" />
                      <span className="text-[10px] font-semibold">Document accessed successfully</span>
                    </div>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="h-6 w-6 shrink-0 rounded-full bg-[#597869] text-white flex items-center justify-center font-bold text-[13px] shadow-sm">2</div>
                    <div className="w-[1.5px] h-full bg-zinc-150 mt-3 -mb-3"></div>
                  </div>
                  <div className="flex-1 pb-3">
                    <h4 className="font-sans font-bold text-[16px] text-zinc-900 mb-2">Select Sheets</h4>
                    <p className="font-sans text-[11.5px] text-zinc-500 mb-4 leading-relaxed pr-2">
                      We detected the following tabs in your document. Select which ones to sync to the master BOQ.
                    </p>
                    
                    <div className="border border-zinc-200/80 rounded-xl overflow-hidden bg-white shadow-sm">
                      {/* Item 1 */}
                      <div className="flex items-center gap-4 p-4 border-b border-zinc-150 bg-[#FAF9F8]">
                        <div className="h-[18px] w-[18px] rounded-[4px] bg-[#597869] flex items-center justify-center text-white cursor-pointer shadow-sm">
                           <Check className="h-[13px] w-[13px] stroke-[3px]" />
                        </div>
                        <FileSpreadsheet className="h-[22px] w-[22px] text-zinc-700/80 stroke-[1.5px]" />
                        <div>
                          <p className="font-sans font-bold text-[13px] text-zinc-900 leading-none mb-1">Structure</p>
                          <p className="font-sans text-[10px] text-zinc-500">450 rows detected</p>
                        </div>
                      </div>
                      {/* Item 2 */}
                      <div className="flex items-center gap-4 p-4 border-b border-zinc-150 bg-[#FAF9F8]">
                        <div className="h-[18px] w-[18px] rounded-[4px] bg-[#597869] flex items-center justify-center text-white cursor-pointer shadow-sm">
                           <Check className="h-[13px] w-[13px] stroke-[3px]" />
                        </div>
                        <FileSpreadsheet className="h-[22px] w-[22px] text-zinc-700/80 stroke-[1.5px]" />
                        <div>
                          <p className="font-sans font-bold text-[13px] text-zinc-900 leading-none mb-1">Electrical</p>
                          <p className="font-sans text-[10px] text-zinc-500">125 rows detected</p>
                        </div>
                      </div>
                      {/* Item 3 */}
                      <div className="flex items-center gap-4 p-4 bg-white">
                        <div className="h-[18px] w-[18px] rounded-[4px] border-[1.5px] border-zinc-300 flex items-center justify-center cursor-pointer bg-white">
                        </div>
                        <FileSpreadsheet className="h-[22px] w-[22px] text-zinc-700/80 stroke-[1.5px]" />
                        <div>
                          <p className="font-sans font-bold text-[13px] text-zinc-900 leading-none mb-1">Plumbing</p>
                          <p className="font-sans text-[10px] text-zinc-500">89 rows detected</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Step 3 */}
                <div className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="h-6 w-6 shrink-0 rounded-full border-2 border-[#597869] flex items-center justify-center">
                      <div className="h-[7px] w-[7px] rounded-full bg-[#597869]"></div>
                    </div>
                  </div>
                  <div className="flex-1">
                    <h4 className="font-sans font-bold text-[16px] text-zinc-900 mb-4">Syncing Data</h4>
                    
                    <div className="p-4 border border-[#E2EBE5] bg-[#F7FAF8] rounded-xl shadow-[0_1px_2px_rgba(89,120,105,0.05)]">
                      <div className="flex justify-between items-end mb-2.5">
                        <div>
                          <p className="font-sans text-[9px] font-bold text-zinc-600 tracking-wider uppercase mb-1.5">PROCESSING 'STRUCTURE'</p>
                          <p className="font-sans text-[11px] text-zinc-500 font-medium">Parsing row 142 of 500...</p>
                        </div>
                        <div className="font-sans font-bold text-[22px] text-[#597869] leading-none">28%</div>
                      </div>
                      <div className="w-full h-[5px] bg-zinc-200/70 rounded-full mb-3.5 overflow-hidden">
                        <div className="h-full bg-[#597869] w-[28%] rounded-full"></div>
                      </div>
                      <div className="flex items-center gap-2 text-zinc-600">
                        <RefreshCw className="h-3 w-3 animate-spin text-[#597869] stroke-[2.5px]" />
                        <span className="font-sans text-[10px] font-medium">Validating quantities and unit rates</span>
                      </div>
                    </div>
                  </div>
                </div>

              </div>

              {/* Sync Drawer footer action */}
              <div className="p-6 border-t border-zinc-150 flex justify-end gap-3 bg-white">
                <button
                  id="cancel-sync-btn"
                  onClick={() => setIsSyncDrawerOpen(false)}
                  className="py-2.5 px-6 border border-zinc-200 text-zinc-700 font-bold text-[11px] rounded-[8px] hover:bg-zinc-50 transition-colors shadow-sm cursor-pointer"
                >
                  Cancel Sync
                </button>
                <button
                  id="run-erp-sync-btn"
                  className="py-2.5 px-7 bg-[#9CA3AF] text-white font-bold text-[11px] rounded-[8px] shadow-sm cursor-not-allowed"
                >
                  Done
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* 5. NEW PROJECT REGISTRATION DIALOG / MODAL */}
      <AnimatePresence>
        {isNewProjectModalOpen && (
          <div id="new-project-modal-overlay" className="fixed inset-0 bg-zinc-900/40 backdrop-blur-sm flex justify-center items-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
              transition={{ duration: 0.2 }}
              className="w-full max-w-[600px] bg-[#FCFAF8] rounded-2xl overflow-hidden shadow-2xl flex flex-col"
            >
              {/* Form container */}
              <form onSubmit={handleCreateProjectSubmit} className="flex flex-col h-full">
                <div className="px-8 pt-8 pb-5 flex justify-between items-start">
                  <div>
                    <h3 className="font-sans font-bold text-[22px] text-zinc-900 tracking-tight">New Project</h3>
                    <p className="font-sans text-[13px] text-zinc-500 mt-1">Enter the foundational details to initialize a new construction space.</p>
                  </div>
                  <button
                    id="close-new-project-modal-top"
                    type="button"
                    onClick={() => setIsNewProjectModalOpen(false)}
                    className="p-1.5 hover:bg-zinc-200/50 rounded-lg text-zinc-500 transition-colors cursor-pointer -mr-2"
                  >
                    <X className="h-5 w-5 stroke-[2px]" />
                  </button>
                </div>
                
                <div className="mx-8 border-t border-zinc-200/60"></div>

                <div className="p-8 space-y-6">
                  {/* Name field */}
                  <div className="space-y-2">
                    <label className="font-sans text-[10px] font-bold text-zinc-800 tracking-wider uppercase block">
                      PROJECT NAME (ชื่อโครงการ) <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="input-project-name"
                      type="text"
                      required
                      placeholder="e.g. Sukhumvit Tower Phase 2"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      className="w-full text-[13px] font-sans p-3 px-4 border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 bg-white transition-all shadow-sm placeholder:text-zinc-300"
                    />
                  </div>

                  {/* Code & Location row */}
                  <div className="grid grid-cols-2 gap-5">
                    <div className="space-y-2">
                      <label className="font-sans text-[10px] font-bold text-zinc-800 tracking-wider uppercase block">
                        PROJECT CODE (รหัสโครงการ) <span className="text-red-500">*</span>
                      </label>
                      <div className="relative flex items-center">
                        <span className="absolute left-4 text-zinc-400 text-sm font-sans font-medium">#</span>
                        <input
                          id="input-project-code"
                          type="text"
                          required
                          placeholder="PRJ-2024-001"
                          value={newCode}
                          onChange={(e) => setNewCode(e.target.value)}
                          className="w-full text-[13px] font-sans p-3 pl-8 border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 bg-white transition-all shadow-sm placeholder:text-zinc-300"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <label className="font-sans text-[10px] font-bold text-zinc-800 tracking-wider uppercase block">LOCATION</label>
                      <div className="relative flex items-center">
                        <svg className="absolute left-3.5 h-4 w-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        <input
                          id="input-project-location"
                          type="text"
                          placeholder="City, District"
                          value={newLocation}
                          onChange={(e) => setNewLocation(e.target.value)}
                          className="w-full text-[13px] font-sans p-3 pl-9 border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 bg-white transition-all shadow-sm placeholder:text-zinc-300"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Dates row */}
                  <div className="grid grid-cols-2 gap-5">
                    <div className="space-y-2 relative">
                      <label className="font-sans text-[10px] font-bold text-zinc-800 tracking-wider uppercase block">START DATE</label>
                      <div className="relative flex items-center">
                        <input
                          id="input-project-start-date"
                          type="date"
                          className="w-full text-[13px] font-sans p-3 px-4 border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 bg-white transition-all shadow-sm text-zinc-500 custom-date-input appearance-none [&::-webkit-calendar-picker-indicator]:opacity-0 [&::-webkit-calendar-picker-indicator]:absolute [&::-webkit-calendar-picker-indicator]:right-0 [&::-webkit-calendar-picker-indicator]:w-full [&::-webkit-calendar-picker-indicator]:h-full [&::-webkit-calendar-picker-indicator]:cursor-pointer"
                        />
                        <svg className="absolute right-3.5 h-[15px] w-[15px] text-zinc-900 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" strokeWidth="2"></rect>
                          <line x1="16" y1="2" x2="16" y2="6" strokeWidth="2"></line>
                          <line x1="8" y1="2" x2="8" y2="6" strokeWidth="2"></line>
                          <line x1="3" y1="10" x2="21" y2="10" strokeWidth="2"></line>
                        </svg>
                      </div>
                    </div>
                    <div className="space-y-2 relative">
                      <label className="font-sans text-[10px] font-bold text-zinc-800 tracking-wider uppercase block">ESTIMATED END DATE</label>
                      <div className="relative flex items-center">
                        <input
                          id="input-project-end-date"
                          type="date"
                          className="w-full text-[13px] font-sans p-3 px-4 border border-zinc-200 rounded-lg focus:outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-400 bg-white transition-all shadow-sm text-zinc-500 custom-date-input appearance-none [&::-webkit-calendar-picker-indicator]:opacity-0 [&::-webkit-calendar-picker-indicator]:absolute [&::-webkit-calendar-picker-indicator]:right-0 [&::-webkit-calendar-picker-indicator]:w-full [&::-webkit-calendar-picker-indicator]:h-full [&::-webkit-calendar-picker-indicator]:cursor-pointer"
                        />
                        <svg className="absolute right-3.5 h-[15px] w-[15px] text-zinc-900 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" strokeWidth="2"></rect>
                          <line x1="16" y1="2" x2="16" y2="6" strokeWidth="2"></line>
                          <line x1="8" y1="2" x2="8" y2="6" strokeWidth="2"></line>
                          <line x1="3" y1="10" x2="21" y2="10" strokeWidth="2"></line>
                        </svg>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="px-8 pb-8 pt-5 bg-[#FCFAF8] flex justify-end items-center gap-6 rounded-b-2xl border-t border-zinc-100">
                  <button
                    id="new-project-cancel-btn"
                    type="button"
                    onClick={() => setIsNewProjectModalOpen(false)}
                    className="text-[11px] font-bold text-zinc-600 hover:text-zinc-900 transition-colors uppercase tracking-wider cursor-pointer"
                  >
                    CANCEL
                  </button>
                  <button
                    id="new-project-submit-btn"
                    type="submit"
                    className="py-2.5 px-5 bg-[#597869] text-white hover:bg-[#486457] font-bold rounded-lg text-[11px] transition-colors shadow-sm flex items-center gap-2 uppercase tracking-wider cursor-pointer"
                  >
                    CREATE & PROCEED TO BOQ
                    <svg className="h-[14px] w-[14px]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
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
