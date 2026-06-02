export type ProjectStatus = 'active' | 'draft' | 'completed' | 'on_hold';
export type ComplianceStatus = 'verified' | 'pending' | 'not_verified';

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

export interface ComplianceItem {
  id: string;
  name: string;
  status: ComplianceStatus;
}

export interface SubcontractorProject {
  id: string;
  code: string;
  name: string;
  role: string;
  contractValue: number;
  status: 'active' | 'completed' | 'on_hold';
}

export interface Subcontractor {
  id: string;
  name: string;
  registeredName: string;
  taxId: string;
  status: 'approved' | 'pending' | 'suspended';
  primaryContact: string;
  phone: string;
  email: string;
  compliance: ComplianceItem[];
  projects: SubcontractorProject[];
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

export type ScreenType = 'dashboard' | 'projects' | 'approvals' | 'insights' | 'chat_ai' | 'user_profile' | 'settings' | 'member_details' | 'suspend_account' | 'company_profile';
