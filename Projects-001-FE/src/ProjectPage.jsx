import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  ArrowDownRight,
  ArrowUpDown,
  ArrowUpRight,
  Calendar,
  CheckCircle2,
  ChevronDown,
  MoreHorizontal,
  Pencil,
  Plus,
  RotateCw,
  SlidersHorizontal,
  TableProperties,
  X,
} from 'lucide-react';
import { motion as Motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  createProject,
  getProjectsData,
  updateProject,
} from './api';
import Loading from './components/Loading';
import CircularProgress from './components/CircularProgress';
import SemiCircleGauge from './components/SemiCircleGauge';
import CompanyFundsCard from './components/funds/CompanyFundsCard';
import { useAdminFeedback } from './components/adminFeedback/adminFeedbackContext';
import { canMutateAdminData, getStoredAuthUser } from './auth';
import { BOQ_V2_ENABLED } from './config/features';

const INITIAL_PROJECT_FORM = {
  name: '',
  project_type: 'COMMERCIAL',
  overhead_percent: '0',
  profit_percent: '0',
  vat_percent: '7',
  contingency_budget: '0',
  status: 'ACTIVE',
};

const PROJECT_TYPE_OPTIONS = ['COMMERCIAL', 'INDUSTRIAL', 'HOTEL', 'WAREHOUSE', 'RESIDENTIAL'];
const PROJECT_STATUS_OPTIONS = ['ACTIVE', 'PLANNING', 'ON_HOLD', 'COMPLETED'];
const currencyFormatter = new Intl.NumberFormat('th-TH', {
  style: 'currency',
  currency: 'THB',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const formatCurrency = (value) => currencyFormatter.format(Number.isFinite(Number(value)) ? Number(value) : 0);

const buttonStyle = {
  border: 'none',
  borderRadius: '8px',
  fontSize: '14px',
  fontWeight: '600',
  cursor: 'pointer',
};

const inputStyle = {
  width: '100%',
  padding: '12px 14px',
  borderRadius: '14px',
  border: '1px solid #dfdfdf',
  fontSize: '14px',
  outline: 'none',
  backgroundColor: 'white',
  color: '#1a1a1a',
};

const fieldGroupStyle = {
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
};

const FilterSelect = ({ icon: Icon, value, onChange, options }) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '10px 16px',
      borderRadius: '8px',
      backgroundColor: 'white',
      border: '1px solid #e0e0e0',
      boxShadow: 'var(--shadow-sm)',
    }}
  >
    {Icon ? <Icon size={18} color="#666" /> : null}
    <select
      value={value}
      onChange={onChange}
      style={{
        border: 'none',
        background: 'transparent',
        fontSize: '14px',
        fontWeight: '500',
        color: '#333',
        outline: 'none',
      }}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
    <ChevronDown size={16} color="#666" />
  </div>
);

const DrawerField = ({ label, children, helper }) => (
  <label style={fieldGroupStyle}>
    <span style={{ fontSize: '12px', fontWeight: '600', color: '#666' }}>{label}</span>
    {children}
    {helper ? <span style={{ fontSize: '12px', color: '#8a8a8a' }}>{helper}</span> : null}
  </label>
);

const ProjectCard = ({ project, index, onClick, onEditName, onOpenBoq, nativeBoqEnabled, canMutate = true }) => {
  const { id, name, spent, total, status, progressPercent, projectType, budgetSource, pendingAmount = 0 } = project;
  const left = total - spent;
  const isOverBudget = left < 0;
  const leftLabel = isOverBudget ? 'Over budget' : 'Left';
  const displayLeft = Math.abs(left);
  const normalizedStatus = String(status || '').toLowerCase();
  const isOnTrack =
    normalizedStatus.includes('active') ||
    normalizedStatus.includes('track') ||
    normalizedStatus.includes('complete') ||
    normalizedStatus.includes('approved');

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(name);
  const [saveError, setSaveError] = useState('');
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setEditName(name);
  }, [name]);

  const handleEditClick = (event) => {
    event.stopPropagation();
    setSaveError('');
    setIsEditing(true);
  };

  const handleSave = async (event) => {
    event.stopPropagation();

    if (editName.trim() === '' || editName === name) {
      setEditName(name);
      setIsEditing(false);
      setSaveError('');
      return;
    }

    try {
      setIsSaving(true);
      setSaveError('');
      await onEditName(id, editName);
      setIsEditing(false);
    } catch (error) {
      setSaveError(error.message || 'Failed to rename project.');
      setEditName(name);
      setIsEditing(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      handleSave(event);
    }
    if (event.key === 'Escape') {
      event.stopPropagation();
      setEditName(name);
      setIsEditing(false);
      setSaveError('');
    }
  };

  return (
    <Motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      style={{
      padding: '24px',
      backgroundColor: 'white',
      borderRadius: '12px',
        boxShadow: 'var(--shadow-sm)',
        display: 'flex',
        flexDirection: 'column',
        gap: '18px',
        cursor: 'pointer',
        border: '1px solid #f0f0f0',
      }}
      onClick={onClick}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ flex: 1, marginRight: '8px' }}>
          {isEditing ? (
            <input
              autoFocus
              type="text"
              value={editName}
              onChange={(event) => setEditName(event.target.value)}
              onBlur={handleSave}
              onKeyDown={handleKeyDown}
              onClick={(event) => event.stopPropagation()}
              disabled={isSaving}
              style={{
                fontSize: '16px',
                fontWeight: '600',
                color: '#1a1a1a',
                border: '1px solid var(--primary)',
                borderRadius: '8px',
                padding: '6px 8px',
                width: '100%',
                outline: 'none',
              }}
            />
          ) : (
            <>
              <h3 style={{ fontSize: '16px', fontWeight: '600', color: '#1a1a1a', margin: 0 }}>{name}</h3>
              <div style={{ fontSize: '12px', color: '#888', marginTop: '4px' }}>{projectType}</div>
            </>
          )}
        </div>

        {!isEditing && canMutate ? (
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                onOpenBoq(project);
              }}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                border: '1px solid #eee',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                color: '#666',
                cursor: 'pointer',
                flexShrink: 0,
                backgroundColor: 'white',
              }}
              title="Open native BOQ workspace"
              disabled={!nativeBoqEnabled}
            >
              <TableProperties size={14} />
            </button>
            <button
              type="button"
              onClick={handleEditClick}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                border: '1px solid #eee',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                color: '#666',
                cursor: 'pointer',
                flexShrink: 0,
                backgroundColor: 'white',
              }}
              title="Rename project"
            >
              <Pencil size={14} />
            </button>
          </div>
        ) : null}
      </div>

      <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
        <CircularProgress
          value={spent}
          max={Math.max(total, 1)}
          color={isOverBudget ? '#de5b52' : '#4f6f64'}
          bgColor={isOverBudget ? '#f8d2ce' : '#c7eadc'}
          label="committed"
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', flex: 1 }}>
          <div>
            <div style={{ fontSize: '12px', color: '#888', marginBottom: '4px' }}>{leftLabel}</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
              <span style={{ fontSize: '20px', fontWeight: 'bold', color: isOverBudget ? '#de5b52' : '#1a1a1a' }}>
                {formatCurrency(displayLeft)}
              </span>
              <span style={{ fontSize: '12px', color: '#888' }}>
                /{formatCurrency(total)}
              </span>
            </div>
          </div>

          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '4px 8px',
              borderRadius: '12px',
              width: 'fit-content',
              fontSize: '11px',
              fontWeight: '600',
              backgroundColor: isOnTrack ? '#eefaf2' : '#fff8e6',
              color: isOnTrack ? '#27ae60' : '#f39c12',
            }}
          >
            {isOnTrack ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
            {status}
          </div>
          <div style={{ fontSize: '12px', color: '#888' }}>
            Progress {progressPercent.toFixed(1)}%{budgetSource ? ` • ${budgetSource}` : ''}
          </div>
          {pendingAmount > 0 ? (
            <div style={{ fontSize: '12px', color: '#8a6d1f', fontWeight: 600 }}>
              Pending queue {formatCurrency(pendingAmount)}
            </div>
          ) : null}
          {saveError ? <div style={{ fontSize: '12px', color: '#de5b52' }}>{saveError}</div> : null}
        </div>
      </div>
    </Motion.div>
  );
};

const ExpenseListItem = ({ name, amount, percentage, isUp }) => (
  <div
    style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '12px 0',
      borderBottom: '1px solid #f5f5f5',
    }}
  >
    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
      <div
        style={{
          width: '40px',
          height: '40px',
          borderRadius: '50%',
          backgroundColor: 'rgba(79, 111, 100, 0.12)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          color: 'var(--primary)',
        }}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
        </svg>
      </div>
      <div>
        <div style={{ fontSize: '14px', fontWeight: '600', color: '#333' }}>{formatCurrency(amount)}</div>
        <div style={{ fontSize: '12px', color: '#888' }}>{name}</div>
      </div>
    </div>

    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        padding: '4px 8px',
        borderRadius: '12px',
        fontSize: '11px',
        fontWeight: '600',
        backgroundColor: isUp ? '#fceaea' : '#eefaf2',
        color: isUp ? '#e74c3c' : '#27ae60',
      }}
    >
      {isUp ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
      {percentage}%
    </div>
  </div>
);

const ProjectPage = () => {
  const { notify } = useAdminFeedback();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [projectForm, setProjectForm] = useState(INITIAL_PROJECT_FORM);
  const [drawerError, setDrawerError] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [amountFilter, setAmountFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState('DEFAULT');
  const canMutateProjects = canMutateAdminData(getStoredAuthUser());

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError('');
        const result = await getProjectsData();
        setProjects(result);
      } catch (loadError) {
        setError(loadError.message || 'Failed to load projects.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const closeDrawer = () => {
    setDrawerOpen(false);
    setProjectForm(INITIAL_PROJECT_FORM);
    setDrawerError('');
  };

  const openCreateDrawer = () => {
    if (!canMutateProjects) return;
    setDrawerOpen(true);
    setProjectForm(INITIAL_PROJECT_FORM);
    setDrawerError('');
  };

  const handleProjectFormChange = (field, value) => {
    setProjectForm((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleCreateProject = async (event) => {
    event.preventDefault();

    try {
      setIsCreating(true);
      setDrawerError('');
      const createdProject = await createProject({
        ...projectForm,
        overhead_percent: Number(projectForm.overhead_percent),
        profit_percent: Number(projectForm.profit_percent),
        vat_percent: Number(projectForm.vat_percent),
        contingency_budget: Number(projectForm.contingency_budget),
      });

      setProjects((current) => [createdProject, ...current]);
      notify({
        tone: 'success',
        title: 'Project created',
        message: `"${createdProject.name}" is ready for BOQ setup.`,
      });
      if (BOQ_V2_ENABLED) {
        closeDrawer();
        navigate(`/project/detail/${createdProject.id}/boq`, {
          state: { projectName: createdProject.name, projectId: createdProject.id },
        });
      } else {
        closeDrawer();
        notify({
          tone: 'info',
          title: 'Native BOQ rollout is disabled',
          message: 'The project was created. Enable the approved BOQ V2 release flag before entering scope.',
        });
      }
    } catch (createError) {
      setDrawerError(createError.message || 'Failed to create project.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleRenameProject = async (projectId, nextName) => {
    const updatedProject = await updateProject(projectId, { name: nextName });

    setProjects((current) =>
      current.map((project) => (project.id === projectId ? { ...project, ...updatedProject } : project))
    );

    notify({
      tone: 'success',
      title: 'Project renamed',
      message: `Project name updated to "${updatedProject.name}".`,
    });
  };

  const resetFilters = () => {
    setStatusFilter('ALL');
    setAmountFilter('ALL');
    setSortBy('DEFAULT');
  };

  const operationsProject = projects.find((project) => project.isSystemOperations);
  const constructionProjects = projects.filter((project) => !project.isSystemOperations);

  const statusOptions = [
    { value: 'ALL', label: 'Status: All' },
    ...Array.from(new Set(constructionProjects.map((project) => project.rawStatus || project.status)))
      .filter(Boolean)
      .sort()
      .map((status) => ({
        value: status,
        label: `Status: ${String(status).replace(/_/g, ' ')}`,
      })),
  ];

  let filteredProjects = [...constructionProjects];

  if (statusFilter !== 'ALL') {
    filteredProjects = filteredProjects.filter((project) => project.rawStatus === statusFilter);
  }

  if (amountFilter === 'UNDER_3000000') {
    filteredProjects = filteredProjects.filter((project) => project.total < 3000000);
  }
  if (amountFilter === 'BETWEEN_3000000_5000000') {
    filteredProjects = filteredProjects.filter((project) => project.total >= 3000000 && project.total <= 5000000);
  }
  if (amountFilter === 'OVER_5000000') {
    filteredProjects = filteredProjects.filter((project) => project.total > 5000000);
  }

  if (sortBy === 'NAME_ASC') {
    filteredProjects.sort((left, right) => left.name.localeCompare(right.name));
  } else if (sortBy === 'BUDGET_DESC') {
    filteredProjects.sort((left, right) => right.total - left.total);
  } else if (sortBy === 'BUDGET_ASC') {
    filteredProjects.sort((left, right) => left.total - right.total);
  } else if (sortBy === 'PROGRESS_DESC') {
    filteredProjects.sort((left, right) => right.progressPercent - left.progressPercent);
  }

  const totalSpent = filteredProjects.reduce((accumulator, project) => accumulator + project.spent, 0);
  const totalBudget = filteredProjects.reduce((accumulator, project) => accumulator + project.total, 0);
  const sortedProjects = [...filteredProjects].sort((left, right) => right.spent - left.spent);

  if (loading) return <Loading />;

  if (error) {
    return (
      <div className="card" style={{ backgroundColor: 'white', color: '#de5b52' }}>
        {error}
      </div>
    );
  }

  return (
    <>
      <div className="project-page-layout">
        <div>
          <div className="project-page-heading">
            <div>
              <h1 style={{ fontSize: '32px', fontWeight: 'bold', color: '#1a1a1a', marginBottom: '4px' }}>Projects</h1>
              <p style={{ color: '#888', fontSize: '14px' }}>Plan Company Operations forecast margin separately from active construction work.</p>
            </div>
            {canMutateProjects ? (
              <button
                type="button"
                onClick={openCreateDrawer}
                style={{
                  ...buttonStyle,
                  backgroundColor: 'var(--primary)',
                  color: 'white',
                  padding: '12px 24px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: 'none',
                }}
              >
                <Plus size={18} />
                Add new project
              </button>
            ) : null}
          </div>

          <CompanyFundsCard
            project={operationsProject}
            canMutate={canMutateProjects}
            onOpen={() => navigate(`/project/detail/${operationsProject.id}`, {
              state: { projectName: operationsProject.name, projectId: operationsProject.id },
            })}
            onAllocate={() => navigate(`/project/detail/${operationsProject.id}?fund_action=allocate`, {
              state: { projectName: operationsProject.name, projectId: operationsProject.id },
            })}
            onSetOpening={() => navigate(`/project/detail/${operationsProject.id}?fund_action=opening`, {
              state: { projectName: operationsProject.name, projectId: operationsProject.id },
            })}
          />

          <div className="project-construction-heading">
            <div>
              <span>CONSTRUCTION PORTFOLIO</span>
              <h2>Active Construction Projects</h2>
            </div>
            <small>{constructionProjects.length} projects</small>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '32px' }}>
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
              <div className="card" style={{ padding: '8px', borderRadius: '12px' }}>
                <Calendar size={20} />
              </div>
              <FilterSelect
                icon={ArrowUpDown}
                value={sortBy}
                onChange={(event) => setSortBy(event.target.value)}
                options={[
                  { value: 'DEFAULT', label: 'Sort: Default' },
                  { value: 'NAME_ASC', label: 'Sort: Name A-Z' },
                  { value: 'BUDGET_DESC', label: 'Sort: Budget high-low' },
                  { value: 'BUDGET_ASC', label: 'Sort: Budget low-high' },
                  { value: 'PROGRESS_DESC', label: 'Sort: Progress high-low' },
                ]}
              />
              <div className="card" style={{ padding: '8px', borderRadius: '50%' }}>
                <SlidersHorizontal size={20} />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
              <FilterSelect
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                options={statusOptions}
              />
              <FilterSelect
                value={amountFilter}
                onChange={(event) => setAmountFilter(event.target.value)}
                options={[
                  { value: 'ALL', label: 'Amount: All' },
                  { value: 'UNDER_3000000', label: 'Amount: Under 3M' },
                  { value: 'BETWEEN_3000000_5000000', label: 'Amount: 3M - 5M' },
                  { value: 'OVER_5000000', label: 'Amount: Over 5M' },
                ]}
              />
              <button
                type="button"
                onClick={resetFilters}
                style={{
                  background: 'transparent',
                  border: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  color: 'var(--primary)',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500',
                }}
              >
                <RotateCw size={16} />
                <span>Reset all</span>
              </button>
            </div>

            <p style={{ fontSize: '12px', color: '#888', marginTop: '8px' }}>{filteredProjects.length} items</p>
          </div>

          {filteredProjects.length === 0 ? (
            <div className="card" style={{ backgroundColor: 'white', color: '#666' }}>
              No projects match the selected filters yet.
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
              {filteredProjects.map((project, index) => (
                <ProjectCard
                  key={project.id || index}
                  project={project}
                  index={index}
                  onEditName={handleRenameProject}
                  onOpenBoq={(selected) => {
                    if (!BOQ_V2_ENABLED) return;
                    navigate(`/project/detail/${selected.id}/boq`, {
                      state: { projectName: selected.name, projectId: selected.id },
                    });
                  }}
                  nativeBoqEnabled={BOQ_V2_ENABLED}
                  canMutate={canMutateProjects}
                  onClick={() =>
                    navigate(`/project/detail/${project.id}`, {
                      state: { projectName: project.name, projectId: project.id },
                    })
                  }
                />
              ))}
            </div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <Motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="card"
        style={{ padding: '24px', backgroundColor: 'white', borderRadius: '12px', border: '1px solid var(--border-color)' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 'bold' }}>Total budget</h3>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  border: '1px solid #eee',
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                }}
              >
                <MoreHorizontal size={16} color="#666" />
              </div>
            </div>

            <div style={{ textAlign: 'center', marginBottom: '16px' }}>
              <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#1a1a1a' }}>
                {formatCurrency(totalBudget)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'center', marginTop: '8px' }}>
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '4px 12px',
                    borderRadius: '12px',
                    fontSize: '12px',
                    fontWeight: '600',
                    backgroundColor: '#eefaf2',
                    color: '#27ae60',
                  }}
                >
                  <CheckCircle2 size={14} />
                  filtered view
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <SemiCircleGauge
                value={totalSpent}
                max={Math.max(totalBudget, 1)}
                color="#4f6f64"
                bgColor="#c7eadc"
                size={260}
                label="committed"
                remainingLabel="left"
                valueFormatter={formatCurrency}
              />
            </div>
          </Motion.div>

          <Motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="card"
            style={{ padding: '24px', backgroundColor: 'white', borderRadius: '12px', border: '1px solid var(--border-color)' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '18px', fontWeight: 'bold' }}>Most expenses</h3>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '12px',
                  color: '#666',
                  border: '1px solid #eee',
                  padding: '4px 8px',
                  borderRadius: '12px',
                }}
              >
                Filtered list <ChevronDown size={14} />
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {sortedProjects.map((project, index) => {
                const percentage = (1.5 + index * 2.3).toFixed(1);
                const isUp = index % 2 === 0;
                return (
                  <ExpenseListItem
                    key={project.id || index}
                    name={project.name}
                    amount={project.spent}
                    percentage={percentage}
                    isUp={isUp}
                  />
                );
              })}
            </div>
          </Motion.div>
        </div>
      </div>

      {drawerOpen ? (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(16, 18, 27, 0.34)',
            zIndex: 40,
            display: 'flex',
            justifyContent: 'flex-end',
          }}
        >
          <div
            style={{
              width: 'min(560px, 100%)',
              height: '100%',
              backgroundColor: 'var(--bg-primary)',
              boxShadow: '-12px 0 30px rgba(47, 46, 44, 0.10)',
              padding: '28px',
              overflowY: 'auto',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
              <div>
                <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Create Project
                </div>
                <h2 style={{ fontSize: '28px', fontWeight: '700', margin: '8px 0 4px', color: '#1a1a1a' }}>
                  New project setup
                </h2>
                <p style={{ fontSize: '14px', color: '#777', margin: 0 }}>
                  Create the project first, then enter scope in the native BOQ workspace.
                </p>
              </div>
              <button
                type="button"
                onClick={closeDrawer}
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  border: '1px solid #e5e5ef',
                  backgroundColor: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                }}
              >
                <X size={18} />
              </button>
            </div>

            {drawerError ? (
              <div
                className="card"
                style={{
                  marginBottom: '18px',
                  backgroundColor: '#fff3f2',
                  color: '#de5b52',
                  border: '1px solid #f5d7d3',
                }}
              >
                {drawerError}
              </div>
            ) : null}

            <form onSubmit={handleCreateProject} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
                <div
                  style={{
                    padding: '18px',
                    backgroundColor: 'white',
                    borderRadius: '20px',
                    border: '1px solid #ece8ff',
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '16px',
                  }}
                >
                  <div style={{ gridColumn: '1 / -1' }}>
                    <DrawerField label="Project name">
                      <input
                        type="text"
                        value={projectForm.name}
                        onChange={(event) => handleProjectFormChange('name', event.target.value)}
                        placeholder="Bangna Warehouse Fit-Out"
                        style={inputStyle}
                        required
                      />
                    </DrawerField>
                  </div>

                  <DrawerField label="Project type">
                    <select
                      value={projectForm.project_type}
                      onChange={(event) => handleProjectFormChange('project_type', event.target.value)}
                      style={inputStyle}
                    >
                      {PROJECT_TYPE_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </DrawerField>

                  <DrawerField label="Status">
                    <select
                      value={projectForm.status}
                      onChange={(event) => handleProjectFormChange('status', event.target.value)}
                      style={inputStyle}
                    >
                      {PROJECT_STATUS_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </DrawerField>

                  <DrawerField label="Overhead %" helper="Stored as percent value on the project.">
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={projectForm.overhead_percent}
                      onChange={(event) => handleProjectFormChange('overhead_percent', event.target.value)}
                      style={inputStyle}
                    />
                  </DrawerField>

                  <DrawerField label="Profit %" helper="Used in project summary and detail view.">
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={projectForm.profit_percent}
                      onChange={(event) => handleProjectFormChange('profit_percent', event.target.value)}
                      style={inputStyle}
                    />
                  </DrawerField>

                  <DrawerField label="VAT %" helper="Defaults to 7.0 for new projects.">
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={projectForm.vat_percent}
                      onChange={(event) => handleProjectFormChange('vat_percent', event.target.value)}
                      style={inputStyle}
                    />
                  </DrawerField>

                  <DrawerField label="Contingency budget" helper="Fallback used only until an active BOQ budget exists.">
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={projectForm.contingency_budget}
                      onChange={(event) => handleProjectFormChange('contingency_budget', event.target.value)}
                      style={inputStyle}
                    />
                  </DrawerField>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
                  <button
                    type="button"
                    onClick={closeDrawer}
                    style={{
                      ...buttonStyle,
                      flex: 1,
                      padding: '14px 16px',
                      backgroundColor: 'white',
                      color: '#555',
                      border: '1px solid #e2e2ea',
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isCreating}
                    style={{
                      ...buttonStyle,
                      flex: 1,
                      padding: '14px 16px',
                      backgroundColor: 'var(--primary)',
                      color: 'white',
                      opacity: isCreating ? 0.7 : 1,
                    }}
                  >
                    {isCreating ? 'Creating...' : 'Create project'}
                  </button>
                </div>
            </form>
          </div>
        </div>
      ) : null}
    </>
  );
};

export default ProjectPage;
