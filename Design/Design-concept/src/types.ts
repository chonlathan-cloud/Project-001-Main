export type ProjectStatus = 'active' | 'draft' | 'completed' | 'on_hold';

export interface BOQItem {
  id: string;
  itemCode: string;
  description: string;
  unit: string;
  quantity: number;
  rate: number;
  amount: number;
  status: 'synced' | 'pending_sync' | 'modified';
}

export interface Project {
  id: string;
  name: string;
  code: string;
  status: ProjectStatus;
  budget: number;
  spent: number;
  progress: number;
  owner: string;
  subcontractorCount: number;
  startDate: string;
  endDate: string;
  description: string;
  boqSynced: boolean;
  boqLastSync?: string;
  location: string;
  boqItems: BOQItem[];
}

export interface ApprovalRequest {
  id: string;
  projectId: string;
  projectName: string;
  title: string;
  subcontractor: string;
  amount: number;
  status: 'pending' | 'approved' | 'rejected';
  date: string;
  description: string;
  category: 'Structural' | 'Electrical' | 'Mechanical' | 'HVAC' | 'Finishes' | 'Civil';
  requestedBy: string;
}

export interface ActivityLog {
  id: string;
  type: 'sync' | 'approval' | 'budget_alteration' | 'status_change';
  projectCode: string;
  projectName: string;
  user: string;
  message: string;
  timestamp: string;
}

export type ScreenType = 'dashboard' | 'projects' | 'approvals' | 'insights';
