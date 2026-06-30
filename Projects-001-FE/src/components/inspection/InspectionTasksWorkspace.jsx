import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  Building2,
  CalendarDays,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  MapPin,
  RefreshCw,
  Search,
} from 'lucide-react';
import {
  createInspectionDefectComment,
  getInputProjectOptions,
  getInspectionDefects,
  getInspectionEvents,
  getInspectionRounds,
  getInspectionZones,
  updateInspectionDefectStatus,
  uploadInspectionFile,
} from '../../api';
import { getStoredAuthUser, isSubcontractorUser, subscribeToAuthChanges } from '../../auth';
import InspectionDefectDrawer from './InspectionDefectDrawer';
import {
  INSPECTION_STATUS_LABELS,
  formatInspectionDate,
  getSeverityTone,
  getStatusTone,
  isInspectionDefectOverdue,
} from './inspectionUtils';

const STATUS_FILTERS = [
  { value: 'ALL', label: 'All' },
  { value: 'OPEN', label: INSPECTION_STATUS_LABELS.OPEN },
  { value: 'IN_PROGRESS', label: INSPECTION_STATUS_LABELS.IN_PROGRESS },
  { value: 'READY_FOR_REVIEW', label: INSPECTION_STATUS_LABELS.READY_FOR_REVIEW },
  { value: 'RESOLVED', label: INSPECTION_STATUS_LABELS.RESOLVED },
];

const STATUS_SORT = {
  OPEN: 0,
  IN_PROGRESS: 1,
  READY_FOR_REVIEW: 2,
  RESOLVED: 3,
};

const roundKey = (projectId, roundId) => `${projectId || ''}::${roundId || ''}`;

const taskKey = (task) => `${task?.project_id || ''}::${task?.round_id || ''}::${task?.id || ''}`;

const normalizeProjectName = (project) =>
  project?.name || project?.project_name || project?.label || project?.project_id || project?.id || 'Project';

const normalizeRoundName = (round) =>
  round?.name || round?.title || round?.display_name || round?.id || 'Inspection Round';

const normalizeStatus = (value) => String(value || 'OPEN').trim().toUpperCase();

const getTaskSearchText = (task) => [
  task.display_no,
  task.title,
  task.description,
  task.category,
  task.project_name,
  task.round_name,
  task.zone_name,
  task.assigned_subcontractor_name,
].filter(Boolean).join(' ').toLowerCase();

function SummaryTile({ icon, label, value, tone = 'neutral' }) {
  const IconComponent = icon;

  return (
    <div className={`inspection-task-summary-card tone-${tone}`}>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <IconComponent size={20} />
    </div>
  );
}

function TaskCard({ task, active, onSelect }) {
  const status = normalizeStatus(task.status);
  const severity = String(task.severity || 'MINOR').toUpperCase();
  const overdue = isInspectionDefectOverdue(task);
  const beforeCount = Array.isArray(task.before_file_ids) ? task.before_file_ids.length : 0;
  const afterCount = Array.isArray(task.after_file_ids) ? task.after_file_ids.length : 0;

  return (
    <button
      type="button"
      className={`inspection-task-card${active ? ' is-active' : ''}${overdue ? ' is-overdue' : ''}`}
      onClick={() => onSelect(task)}
    >
      <div className="inspection-task-card-head">
        <div className="inspection-badge-row">
          <span className={`inspection-badge tone-${getStatusTone(status)}`}>
            {INSPECTION_STATUS_LABELS[status] || status}
          </span>
          <span className={`inspection-badge tone-${getSeverityTone(severity)}`}>{severity}</span>
        </div>
        <strong>{task.display_no || task.id || 'Defect'}</strong>
      </div>

      <div className="inspection-task-title">
        <strong>{task.title || task.category || 'Untitled defect'}</strong>
        <span>{task.description || 'No defect notes provided.'}</span>
      </div>

      <div className="inspection-task-meta">
        <div>
          <Building2 size={15} />
          <span>{task.project_name}</span>
        </div>
        <div>
          <ClipboardCheck size={15} />
          <span>{task.round_name}</span>
        </div>
        <div>
          <MapPin size={15} />
          <span>{task.zone_name || task.zone_id || '-'}</span>
        </div>
        <div className={overdue ? 'danger' : ''}>
          <CalendarDays size={15} />
          <span>{formatInspectionDate(task.due_date)}</span>
        </div>
      </div>

      <div className="inspection-task-card-foot">
        <span>{beforeCount} before</span>
        <span>{afterCount} after</span>
      </div>
    </button>
  );
}

export default function InspectionTasksWorkspace() {
  const [authUser, setAuthUser] = useState(() => getStoredAuthUser());
  const [tasks, setTasks] = useState([]);
  const [projects, setProjects] = useState([]);
  const [zonesByRound, setZonesByRound] = useState({});
  const [selectedTask, setSelectedTask] = useState(null);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchDraft, setSearchDraft] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [events, setEvents] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [workflowError, setWorkflowError] = useState('');
  const isSubcontractor = isSubcontractorUser(authUser);

  const loadTasks = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const projectOptions = await getInputProjectOptions();
      const nextProjects = (Array.isArray(projectOptions) ? projectOptions : [])
        .map((project) => ({
          ...project,
          project_id: project.project_id || project.id || '',
          project_name: normalizeProjectName(project),
        }))
        .filter((project) => project.project_id);

      const nextZonesByRound = {};
      const projectTaskGroups = await Promise.all(
        nextProjects.map(async (project) => {
          const rounds = await getInspectionRounds(project.project_id).catch(() => []);
          const roundList = Array.isArray(rounds) ? rounds : [];
          const roundTaskGroups = await Promise.all(
            roundList.map(async (round) => {
              const roundId = round.id || round.round_id || '';
              if (!roundId) return [];

              const [zonesPayload, defectsPayload] = await Promise.all([
                getInspectionZones(project.project_id, roundId).catch(() => []),
                getInspectionDefects(project.project_id, roundId).catch(() => []),
              ]);
              const zoneList = Array.isArray(zonesPayload) ? zonesPayload : [];
              const defectList = Array.isArray(defectsPayload) ? defectsPayload : [];
              const zoneNameById = new Map(zoneList.map((zone) => [zone.id, zone.name || zone.id]));
              const key = roundKey(project.project_id, roundId);
              nextZonesByRound[key] = zoneList;

              return defectList.map((defect) => ({
                ...defect,
                project_id: project.project_id,
                project_name: project.project_name,
                round_id: roundId,
                round_name: normalizeRoundName(round),
                zone_name: defect.zone_name || zoneNameById.get(defect.zone_id) || defect.zone_id || '',
              }));
            })
          );
          return roundTaskGroups.flat();
        })
      );

      const nextTasks = projectTaskGroups
        .flat()
        .sort((left, right) => {
          const leftStatus = normalizeStatus(left.status);
          const rightStatus = normalizeStatus(right.status);
          const statusDelta = (STATUS_SORT[leftStatus] ?? 99) - (STATUS_SORT[rightStatus] ?? 99);
          if (statusDelta) return statusDelta;
          const leftDue = left.due_date ? new Date(left.due_date).getTime() : Number.MAX_SAFE_INTEGER;
          const rightDue = right.due_date ? new Date(right.due_date).getTime() : Number.MAX_SAFE_INTEGER;
          return leftDue - rightDue;
        });

      setProjects(nextProjects);
      setZonesByRound(nextZonesByRound);
      setTasks(nextTasks);
      setSelectedTask((current) => {
        if (!current) return current;
        return nextTasks.find((task) => taskKey(task) === taskKey(current)) || null;
      });
    } catch (loadError) {
      setTasks([]);
      setProjects([]);
      setZonesByRound({});
      setSelectedTask(null);
      setError(loadError.message || 'Failed to load assigned inspection defects.');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTaskEvents = useCallback(async (task) => {
    if (!task?.project_id || !task?.round_id || !task?.id) {
      setEvents([]);
      return;
    }

    try {
      setLoadingEvents(true);
      const payload = await getInspectionEvents(task.project_id, task.round_id, task.id);
      setEvents(Array.isArray(payload) ? payload : []);
    } catch {
      setEvents([]);
    } finally {
      setLoadingEvents(false);
    }
  }, []);

  useEffect(() => {
    return subscribeToAuthChanges(() => {
      setAuthUser(getStoredAuthUser());
    });
  }, []);

  useEffect(() => {
    if (!isSubcontractor) {
      setLoading(false);
      setTasks([]);
      return;
    }
    loadTasks();
  }, [isSubcontractor, loadTasks]);

  useEffect(() => {
    setWorkflowError('');
    loadTaskEvents(selectedTask);
  }, [selectedTask, loadTaskEvents]);

  const taskCounts = useMemo(() => {
    const counts = {
      ALL: tasks.length,
      OPEN: 0,
      IN_PROGRESS: 0,
      READY_FOR_REVIEW: 0,
      RESOLVED: 0,
      OVERDUE: 0,
    };
    tasks.forEach((task) => {
      const status = normalizeStatus(task.status);
      if (Object.prototype.hasOwnProperty.call(counts, status)) counts[status] += 1;
      if (isInspectionDefectOverdue(task)) counts.OVERDUE += 1;
    });
    return counts;
  }, [tasks]);

  const filteredTasks = useMemo(() => {
    const searchValue = searchDraft.trim().toLowerCase();
    return tasks.filter((task) => {
      const status = normalizeStatus(task.status);
      if (statusFilter !== 'ALL' && status !== statusFilter) return false;
      if (!searchValue) return true;
      return getTaskSearchText(task).includes(searchValue);
    });
  }, [searchDraft, statusFilter, tasks]);

  const selectedZones = selectedTask
    ? zonesByRound[roundKey(selectedTask.project_id, selectedTask.round_id)] || []
    : [];

  const refreshWorkflowData = async (task) => {
    await Promise.all([loadTasks(), loadTaskEvents(task)]);
  };

  const handleStatusChange = async (task, status, comment = null) => {
    if (!task?.project_id || !task?.round_id || !task?.id || workflowBusy) return;

    try {
      setWorkflowBusy(true);
      setWorkflowError('');
      await updateInspectionDefectStatus(task.project_id, task.round_id, task.id, {
        status,
        comment,
      });
      await refreshWorkflowData(task);
    } catch (statusError) {
      setWorkflowError(statusError.message || 'Failed to update inspection status.');
    } finally {
      setWorkflowBusy(false);
    }
  };

  const handleAddComment = async (task, comment) => {
    if (!task?.project_id || !task?.round_id || !task?.id || workflowBusy) return;

    try {
      setWorkflowBusy(true);
      setWorkflowError('');
      await createInspectionDefectComment(task.project_id, task.round_id, task.id, { comment });
      await loadTaskEvents(task);
    } catch (commentError) {
      setWorkflowError(commentError.message || 'Failed to add inspection comment.');
    } finally {
      setWorkflowBusy(false);
    }
  };

  const handleUploadAfterPhotos = async (task, files = []) => {
    if (!task?.project_id || !task?.round_id || !task?.id || workflowBusy || !files.length) return;

    try {
      setWorkflowBusy(true);
      setWorkflowError('');
      for (const file of files) {
        const formData = new FormData();
        formData.append('kind', 'AFTER_PHOTO');
        formData.append('zone_id', task.zone_id);
        formData.append('defect_id', task.id);
        formData.append('file', file);
        await uploadInspectionFile(task.project_id, task.round_id, formData);
      }
      await refreshWorkflowData(task);
    } catch (uploadError) {
      setWorkflowError(uploadError.message || 'Failed to upload after photos.');
    } finally {
      setWorkflowBusy(false);
    }
  };

  if (!isSubcontractor) {
    return (
      <section className="inspection-workspace">
        <div className="inspection-hero">
          <div>
            <div className="inspection-kicker">
              <ClipboardCheck size={16} />
              Assigned Inspection Work
            </div>
            <h2>Subcontractor work defects</h2>
            <div className="inspection-hero-meta">
              <span>Subcontractor access only</span>
            </div>
          </div>
        </div>

        <section className="inspection-empty-state">
          <AlertCircle size={26} />
          <div>
            <h3>This page is for subcontractor accounts</h3>
            <p>Admin users can manage inspection defects from the project inspection workspace.</p>
          </div>
        </section>
      </section>
    );
  }

  return (
    <section className="inspection-workspace">
      <div className="inspection-hero">
        <div>
          <div className="inspection-kicker">
            <ClipboardCheck size={16} />
            Assigned Inspection Work
          </div>
          <h2>My assigned defects</h2>
          <div className="inspection-hero-meta">
            <span>{projects.length} projects</span>
            <span>{tasks.length} defects</span>
            <span>{taskCounts.OVERDUE} overdue</span>
          </div>
        </div>
        <div className="inspection-hero-score">
          <span>{taskCounts.READY_FOR_REVIEW}</span>
          <small>ready for review</small>
        </div>
      </div>

      {error ? <div className="inspection-alert danger">{error}</div> : null}

      <div className="inspection-task-summary-grid">
        <SummaryTile icon={Clock3} label="Open" value={taskCounts.OPEN} tone="danger" />
        <SummaryTile icon={RefreshCw} label="In progress" value={taskCounts.IN_PROGRESS} />
        <SummaryTile icon={CheckCircle2} label="Ready" value={taskCounts.READY_FOR_REVIEW} tone="warning" />
        <SummaryTile icon={CheckCircle2} label="Resolved" value={taskCounts.RESOLVED} tone="positive" />
      </div>

      <div className="inspection-task-toolbar">
        <div className="inspection-local-tabs" role="tablist" aria-label="Filter assigned defects by status">
          {STATUS_FILTERS.map((filter) => (
            <button
              key={filter.value}
              type="button"
              className={statusFilter === filter.value ? 'active' : ''}
              onClick={() => setStatusFilter(filter.value)}
            >
              {filter.label}
              <span>{taskCounts[filter.value]}</span>
            </button>
          ))}
        </div>
        <div className="inspection-task-search">
          <Search size={16} />
          <input
            type="search"
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder="Search project, zone, defect"
          />
        </div>
        <button
          type="button"
          className="inspection-button secondary"
          onClick={loadTasks}
          disabled={loading}
        >
          <RefreshCw size={16} />
          {loading ? 'Refreshing' : 'Refresh'}
        </button>
      </div>

      {loading ? (
        <section className="inspection-empty-band">
          <RefreshCw size={26} className="inspection-spin" />
          <div>
            <h3>Loading assigned defects</h3>
            <p>Inspection work assigned to this subcontractor will appear here.</p>
          </div>
        </section>
      ) : filteredTasks.length ? (
        <div className="inspection-task-list">
          {filteredTasks.map((task) => (
            <TaskCard
              key={taskKey(task)}
              task={task}
              active={selectedTask ? taskKey(task) === taskKey(selectedTask) : false}
              onSelect={setSelectedTask}
            />
          ))}
        </div>
      ) : (
        <section className="inspection-empty-state">
          <ClipboardCheck size={26} />
          <div>
            <h3>No assigned defects</h3>
            <p>Assigned inspection defects will appear here after an admin assigns work to this account.</p>
          </div>
        </section>
      )}

      <InspectionDefectDrawer
        mode={selectedTask ? 'detail' : ''}
        defect={selectedTask}
        zones={selectedZones}
        categories={[]}
        subcontractors={[]}
        roleContext={{ canStaff: false, isSubcontractor: true, user: authUser }}
        events={events}
        loadingEvents={loadingEvents}
        workflowBusy={workflowBusy}
        workflowError={workflowError}
        onClose={() => setSelectedTask(null)}
        onStatusChange={handleStatusChange}
        onAddComment={handleAddComment}
        onUploadAfterPhotos={handleUploadAfterPhotos}
      />
    </section>
  );
}
