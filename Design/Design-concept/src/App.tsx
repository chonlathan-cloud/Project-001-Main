/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import Sidebar from './components/Sidebar';
import DashboardScreen from './components/DashboardScreen';
import ProjectsScreen from './components/ProjectsScreen';
import ApprovalsScreen from './components/ApprovalsScreen';
import InsightsScreen from './components/InsightsScreen';
import { Project, ApprovalRequest, ActivityLog, ScreenType } from './types';
import { INITIAL_PROJECTS, INITIAL_APPROVALS, INITIAL_ACTIVITY } from './data';

export default function App() {
  const [currentScreen, setScreen] = useState<ScreenType>('dashboard');
  const [projects, setProjects] = useState<Project[]>(INITIAL_PROJECTS);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>(INITIAL_APPROVALS);
  const [activities, setActivities] = useState<ActivityLog[]>(INITIAL_ACTIVITY);
  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);

  // Dynamic log generator helper
  const addActivityLog = (message: string, code: string, name: string, type: ActivityLog['type']) => {
    const currentTimestamp = new Date().toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
      hour12: true
    });

    const newLog: ActivityLog = {
      id: `ACT-${Math.floor(100 + Math.random() * 900)}`,
      type,
      projectCode: code,
      projectName: name,
      user: 'James Harrison',
      message,
      timestamp: currentTimestamp
    };

    setActivities((prev) => [newLog, ...prev]);
  };

  // Master Approval workflow action
  const handleApprove = (id: string) => {
    const freshApprovals = approvals.map((req) => {
      if (req.id === id) {
        return { ...req, status: 'approved' as const };
      }
      return req;
    });

    setApprovals(freshApprovals);

    // Apply financial cost impact to the parent project
    const targetedReq = approvals.find((r) => r.id === id);
    if (targetedReq) {
      setProjects((prevProjects) =>
        prevProjects.map((p) => {
          if (p.id === targetedReq.projectId) {
            const nextSpent = Math.min(p.spent + targetedReq.amount, p.budget);
            const nextProgress = Math.min(parseFloat(((nextSpent / p.budget) * 100).toFixed(1)), 100);
            return {
              ...p,
              spent: nextSpent,
              progress: nextProgress,
            };
          }
          return p;
        })
      );

      addActivityLog(
        `Approved change order of $${targetedReq.amount.toLocaleString()} for subcontractor ${targetedReq.subcontractor}`,
        targetedReq.projectId,
        targetedReq.projectName,
        'approval'
      );
    }
  };

  // Master Reject workflow action
  const handleReject = (id: string) => {
    const freshApprovals = approvals.map((req) => {
      if (req.id === id) {
        return { ...req, status: 'rejected' as const };
      }
      return req;
    });

    setApprovals(freshApprovals);

    const targetedReq = approvals.find((r) => r.id === id);
    if (targetedReq) {
      addActivityLog(
        `Disapproved change order request for ${targetedReq.title}`,
        targetedReq.projectId,
        targetedReq.projectName,
        'status_change'
      );
    }
  };

  // Create Project handler
  const handleAddProject = (newProj: Project) => {
    setProjects((prev) => [newProj, ...prev]);
    addActivityLog(
      `Initialized project entity ${newProj.name} (${newProj.code}) with $${newProj.budget.toLocaleString()} default budget`,
      newProj.code,
      newProj.name,
      'status_change'
    );
  };

  // Update Project (e.g. after Syncing BOQ)
  const handleUpdateProject = (updatedProj: Project) => {
    setProjects((prev) =>
      prev.map((proj) => (proj.id === updatedProj.id ? updatedProj : proj))
    );
  };

  // Count pending approvals
  const pendingApprovalsCount = approvals.filter((u) => u.status === 'pending').length;

  return (
    <div className="flex h-screen bg-zinc-100 font-sans text-zinc-900 antialiased overflow-hidden">
      {/* 1. Sidebar Panel */}
      <Sidebar
        currentScreen={currentScreen}
        setScreen={setScreen}
        pendingApprovalsCount={pendingApprovalsCount}
      />

      {/* 2. Primary Workspace Panel */}
      <main id="main-content-scroller" className="flex-1 overflow-y-auto pl-64 transition-all duration-150 h-screen">
        <div className="max-w-6xl mx-auto px-8 py-8 md:py-12">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentScreen}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.15, ease: 'easeInOut' }}
            >
              {currentScreen === 'dashboard' && (
                <DashboardScreen
                  projects={projects}
                  approvals={approvals}
                  activities={activities}
                  setScreen={setScreen}
                  handleApprove={handleApprove}
                  handleReject={handleReject}
                  openNewProjectModal={() => setIsNewProjectModalOpen(true)}
                />
              )}

              {currentScreen === 'projects' && (
                <ProjectsScreen
                  projects={projects}
                  onAddProject={handleAddProject}
                  onUpdateProject={handleUpdateProject}
                  onAddActivity={(msg, code, name, type) => addActivityLog(msg, code, name, type)}
                  isNewProjectModalOpen={isNewProjectModalOpen}
                  setIsNewProjectModalOpen={setIsNewProjectModalOpen}
                />
              )}

              {currentScreen === 'approvals' && (
                <ApprovalsScreen
                  approvals={approvals}
                  handleApprove={handleApprove}
                  handleReject={handleReject}
                />
              )}

              {currentScreen === 'insights' && (
                <InsightsScreen projects={projects} />
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

