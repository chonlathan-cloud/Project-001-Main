import { useCallback, useEffect, useMemo, useState } from 'react';
import { ClipboardCheck, FileText, Map, Table2 } from 'lucide-react';
import {
  createInspectionDefectComment,
  createInspectionDefect,
  createInspectionReportLog,
  createInspectionRound,
  createInspectionZone,
  getInspectionEvents,
  getInspectionCategories,
  getInspectionDefects,
  getInspectionReportLogs,
  getInspectionRounds,
  getInspectionSummary,
  getInspectionZones,
  getSettingSubcontractors,
  updateInspectionDefectStatus,
  uploadInspectionFile,
} from '../../api';
import {
  getStoredAuthUser,
  isAdminUser,
  isOwnerUser,
  isSubcontractorUser,
  subscribeToAuthChanges,
} from '../../auth';
import InspectionDefectDrawer from './InspectionDefectDrawer';
import InspectionDefectTable from './InspectionDefectTable';
import InspectionMap from './InspectionMap';
import InspectionOverview from './InspectionOverview';
import InspectionReportView from './InspectionReportView';
import InspectionRoundPicker from './InspectionRoundPicker';
import { formatInspectionDate } from './inspectionUtils';

const EMPTY_CREATE_DRAFT = {
  name: '',
  description: '',
  targetCloseDate: '',
};

const LOCAL_VIEWS = [
  { value: 'overview', label: 'Overview', icon: ClipboardCheck },
  { value: 'map', label: 'Inspect Map', icon: Map },
  { value: 'register', label: 'Defect Register', icon: Table2 },
  { value: 'reports', label: 'Reports', icon: FileText },
];

function toTargetCloseAt(value) {
  return value ? `${value}T17:00:00+07:00` : null;
}

function useInitialSelectedRound(rounds, selectedRoundId) {
  return useMemo(() => {
    if (!rounds.length) return '';
    if (selectedRoundId && rounds.some((round) => round.id === selectedRoundId)) {
      return selectedRoundId;
    }
    const activeRound = rounds.find((round) => String(round.status || '').toUpperCase() === 'ACTIVE');
    return (activeRound || rounds[0]).id;
  }, [rounds, selectedRoundId]);
}

function InspectionPlaceholder({ view }) {
  const viewCopy = {
    map: {
      title: 'Inspect Map',
      detail: 'No plan or zone data is available for this round yet.',
    },
    register: {
      title: 'Defect Register',
      detail: 'No defect rows are available for this round yet.',
    },
    reports: {
      title: 'Reports',
      detail: 'No report logs are available for this round yet.',
    },
  };
  const copy = viewCopy[view] || viewCopy.map;

  return (
    <section className="inspection-placeholder">
      <div>
        <h3>{copy.title}</h3>
        <p>{copy.detail}</p>
      </div>
    </section>
  );
}

export default function InspectionWorkspace({ projectId, projectName }) {
  const [rounds, setRounds] = useState([]);
  const [selectedRoundId, setSelectedRoundId] = useState('');
  const [summary, setSummary] = useState(null);
  const [categories, setCategories] = useState([]);
  const [activeView, setActiveView] = useState('overview');
  const [loadingRounds, setLoadingRounds] = useState(true);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [error, setError] = useState('');
  const [summaryError, setSummaryError] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createDraft, setCreateDraft] = useState(EMPTY_CREATE_DRAFT);
  const [zones, setZones] = useState([]);
  const [defects, setDefects] = useState([]);
  const [subcontractors, setSubcontractors] = useState([]);
  const [selectedZoneId, setSelectedZoneId] = useState('');
  const [selectedDefectId, setSelectedDefectId] = useState('');
  const [draftCoordinate, setDraftCoordinate] = useState(null);
  const [loadingInspectionData, setLoadingInspectionData] = useState(false);
  const [mapError, setMapError] = useState('');
  const [creatingZone, setCreatingZone] = useState(false);
  const [uploadingPlan, setUploadingPlan] = useState(false);
  const [savingDefect, setSavingDefect] = useState(false);
  const [defectEvents, setDefectEvents] = useState([]);
  const [loadingEvents, setLoadingEvents] = useState(false);
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [workflowError, setWorkflowError] = useState('');
  const [authUser, setAuthUser] = useState(() => getStoredAuthUser());
  const [reportLogs, setReportLogs] = useState([]);
  const [loadingReportLogs, setLoadingReportLogs] = useState(false);
  const [printingReport, setPrintingReport] = useState(false);
  const [reportError, setReportError] = useState('');
  const nextSelectedRoundId = useInitialSelectedRound(rounds, selectedRoundId);

  const selectedRound = rounds.find((round) => round.id === selectedRoundId) || null;
  const selectedDefect = defects.find((defect) => defect.id === selectedDefectId) || null;
  const roleContext = {
    canStaff: isOwnerUser(authUser) || isAdminUser(authUser),
    isSubcontractor: isSubcontractorUser(authUser),
    user: authUser,
  };

  const loadRounds = async ({ preserveSelection = true } = {}) => {
    if (!projectId) return;

    try {
      setLoadingRounds(true);
      setError('');
      const [roundItems, categoryPayload] = await Promise.all([
        getInspectionRounds(projectId),
        getInspectionCategories(projectId).catch(() => null),
      ]);
      const nextRounds = Array.isArray(roundItems) ? roundItems : [];
      setRounds(nextRounds);
      setCategories(Array.isArray(categoryPayload?.categories) ? categoryPayload.categories : []);

      if (!preserveSelection || !selectedRoundId || !nextRounds.some((round) => round.id === selectedRoundId)) {
        const activeRound = nextRounds.find((round) => String(round.status || '').toUpperCase() === 'ACTIVE');
        setSelectedRoundId((activeRound || nextRounds[0])?.id || '');
      }
    } catch (loadError) {
      setRounds([]);
      setSelectedRoundId('');
      setError(loadError.message || 'Failed to load inspection rounds.');
    } finally {
      setLoadingRounds(false);
    }
  };

  useEffect(() => {
    loadRounds({ preserveSelection: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    return subscribeToAuthChanges(() => {
      setAuthUser(getStoredAuthUser());
    });
  }, []);

  useEffect(() => {
    if (nextSelectedRoundId && nextSelectedRoundId !== selectedRoundId) {
      setSelectedRoundId(nextSelectedRoundId);
    }
  }, [nextSelectedRoundId, selectedRoundId]);

  const loadSummary = useCallback(async () => {
    if (!projectId || !selectedRoundId) {
      setSummary(null);
      setSummaryError('');
      return;
    }

    try {
      setLoadingSummary(true);
      setSummaryError('');
      const payload = await getInspectionSummary(projectId, selectedRoundId);
      setSummary(payload);
    } catch (loadError) {
      setSummary(null);
      setSummaryError(loadError.message || 'Failed to load inspection summary.');
    } finally {
      setLoadingSummary(false);
    }
  }, [projectId, selectedRoundId]);

  const loadInspectionData = useCallback(
    async ({ preserveZone = true } = {}) => {
      if (!projectId || !selectedRoundId) {
        setZones([]);
        setDefects([]);
        setSubcontractors([]);
        setSelectedZoneId('');
        setSelectedDefectId('');
        setDraftCoordinate(null);
        setMapError('');
        return;
      }

      try {
        setLoadingInspectionData(true);
        setMapError('');
        const [zoneItems, defectItems, subcontractorItems] = await Promise.all([
          getInspectionZones(projectId, selectedRoundId),
          getInspectionDefects(projectId, selectedRoundId),
          getSettingSubcontractors().catch(() => []),
        ]);
        const nextZones = Array.isArray(zoneItems) ? zoneItems : [];
        const nextDefects = Array.isArray(defectItems) ? defectItems : [];
        setZones(nextZones);
        setDefects(nextDefects);
        setSubcontractors(Array.isArray(subcontractorItems) ? subcontractorItems : []);
        setSelectedZoneId((current) => {
          if (preserveZone && current && nextZones.some((zone) => zone.id === current)) {
            return current;
          }
          return nextZones[0]?.id || '';
        });
        setSelectedDefectId((current) => {
          if (current && nextDefects.some((defect) => defect.id === current)) {
            return current;
          }
          return '';
        });
      } catch (loadError) {
        setZones([]);
        setDefects([]);
        setMapError(loadError.message || 'Failed to load inspection map data.');
      } finally {
        setLoadingInspectionData(false);
      }
    },
    [projectId, selectedRoundId]
  );

  const loadDefectEvents = useCallback(
    async (defectId) => {
      if (!projectId || !selectedRoundId || !defectId) {
        setDefectEvents([]);
        return;
      }

      try {
        setLoadingEvents(true);
        const payload = await getInspectionEvents(projectId, selectedRoundId, defectId);
        setDefectEvents(Array.isArray(payload) ? payload : []);
      } catch {
        setDefectEvents([]);
      } finally {
        setLoadingEvents(false);
      }
    },
    [projectId, selectedRoundId]
  );

  const loadReportLogs = useCallback(async () => {
    if (!projectId || !selectedRoundId || !roleContext.canStaff) {
      setReportLogs([]);
      setReportError('');
      return;
    }

    try {
      setLoadingReportLogs(true);
      setReportError('');
      const payload = await getInspectionReportLogs(projectId, selectedRoundId);
      setReportLogs(Array.isArray(payload) ? payload : []);
    } catch (loadError) {
      setReportLogs([]);
      setReportError(loadError.message || 'Failed to load inspection report logs.');
    } finally {
      setLoadingReportLogs(false);
    }
  }, [projectId, selectedRoundId, roleContext.canStaff]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    setSelectedZoneId('');
    setSelectedDefectId('');
    setDraftCoordinate(null);
    loadInspectionData({ preserveZone: false });
  }, [loadInspectionData]);

  useEffect(() => {
    if (selectedDefectId && !draftCoordinate) {
      loadDefectEvents(selectedDefectId);
    } else {
      setDefectEvents([]);
    }
  }, [selectedDefectId, draftCoordinate, loadDefectEvents]);

  useEffect(() => {
    if (activeView === 'reports') {
      loadReportLogs();
    }
  }, [activeView, loadReportLogs]);

  const handleCreateRound = async (event) => {
    event.preventDefault();
    const name = createDraft.name.trim();
    if (!name || creating) return;

    try {
      setCreating(true);
      setError('');
      const createdRound = await createInspectionRound(projectId, {
        name,
        description: createDraft.description.trim() || null,
        target_close_at: toTargetCloseAt(createDraft.targetCloseDate),
      });
      setCreateDraft(EMPTY_CREATE_DRAFT);
      setCreateOpen(false);
      await loadRounds({ preserveSelection: false });
      setSelectedRoundId(createdRound.id);
      setActiveView('overview');
    } catch (createError) {
      setError(createError.message || 'Failed to create inspection round.');
    } finally {
      setCreating(false);
    }
  };

  const handleCreateZone = async (payload) => {
    if (!projectId || !selectedRoundId || creatingZone || !roleContext.canStaff) return null;

    try {
      setCreatingZone(true);
      setMapError('');
      const createdZone = await createInspectionZone(projectId, selectedRoundId, payload);
      await loadInspectionData({ preserveZone: false });
      setSelectedZoneId(createdZone.id);
      return createdZone;
    } catch (createError) {
      setMapError(createError.message || 'Failed to create inspection zone.');
      return null;
    } finally {
      setCreatingZone(false);
    }
  };

  const handleUploadPlan = async (file, zoneId) => {
    if (!projectId || !selectedRoundId || !zoneId || !file || uploadingPlan || !roleContext.canStaff) return;

    try {
      setUploadingPlan(true);
      setMapError('');
      const formData = new FormData();
      formData.append('kind', 'PLAN_IMAGE');
      formData.append('zone_id', zoneId);
      formData.append('file', file);
      await uploadInspectionFile(projectId, selectedRoundId, formData);
      await loadInspectionData();
    } catch (uploadError) {
      setMapError(uploadError.message || 'Failed to upload inspection plan.');
    } finally {
      setUploadingPlan(false);
    }
  };

  const handleStartDefect = (coordinate) => {
    if (!roleContext.canStaff) return;
    const zoneId = coordinate?.zoneId || selectedZoneId;
    if (!zoneId) return;
    setSelectedDefectId('');
    setWorkflowError('');
    setDraftCoordinate({
      zoneId,
      planX: coordinate?.planX ?? null,
      planY: coordinate?.planY ?? null,
    });
  };

  const handleSelectDefect = (defectId) => {
    setDraftCoordinate(null);
    setWorkflowError('');
    setSelectedDefectId(defectId);
  };

  const handleSelectZone = (zoneId) => {
    setSelectedZoneId(zoneId);
    setSelectedDefectId('');
    setDraftCoordinate(null);
    setWorkflowError('');
  };

  const handleCloseDrawer = () => {
    setSelectedDefectId('');
    setDraftCoordinate(null);
    setWorkflowError('');
  };

  const handleCreateDefect = async (payload, beforePhotoFiles = []) => {
    if (!projectId || !selectedRoundId || savingDefect || !roleContext.canStaff) return;

    let createdDefect = null;
    try {
      setSavingDefect(true);
      setMapError('');
      createdDefect = await createInspectionDefect(projectId, selectedRoundId, payload);

      for (const file of beforePhotoFiles) {
        const formData = new FormData();
        formData.append('kind', 'BEFORE_PHOTO');
        formData.append('zone_id', payload.zone_id);
        formData.append('defect_id', createdDefect.id);
        formData.append('file', file);
        await uploadInspectionFile(projectId, selectedRoundId, formData);
      }

      setDraftCoordinate(null);
      await Promise.all([loadInspectionData(), loadSummary()]);
      setSelectedDefectId(createdDefect.id);
    } catch (createError) {
      setMapError(createError.message || 'Failed to save inspection defect.');
      if (createdDefect?.id) {
        await loadInspectionData();
        setSelectedDefectId(createdDefect.id);
        setDraftCoordinate(null);
      }
    } finally {
      setSavingDefect(false);
    }
  };

  const refreshWorkflowData = async (defectId = selectedDefectId) => {
    await Promise.all([loadInspectionData(), loadSummary(), loadDefectEvents(defectId)]);
  };

  const handleStatusChange = async (defect, status, comment = null) => {
    if (!projectId || !selectedRoundId || !defect?.id || workflowBusy) return;

    try {
      setWorkflowBusy(true);
      setWorkflowError('');
      await updateInspectionDefectStatus(projectId, selectedRoundId, defect.id, {
        status,
        comment,
      });
      await refreshWorkflowData(defect.id);
    } catch (statusError) {
      setWorkflowError(statusError.message || 'Failed to update inspection status.');
    } finally {
      setWorkflowBusy(false);
    }
  };

  const handleAddComment = async (defect, comment) => {
    if (!projectId || !selectedRoundId || !defect?.id || workflowBusy) return;

    try {
      setWorkflowBusy(true);
      setWorkflowError('');
      await createInspectionDefectComment(projectId, selectedRoundId, defect.id, { comment });
      await loadDefectEvents(defect.id);
    } catch (commentError) {
      setWorkflowError(commentError.message || 'Failed to add inspection comment.');
    } finally {
      setWorkflowBusy(false);
    }
  };

  const handleUploadAfterPhotos = async (defect, files = []) => {
    if (!projectId || !selectedRoundId || !defect?.id || workflowBusy || !files.length) return;

    try {
      setWorkflowBusy(true);
      setWorkflowError('');
      for (const file of files) {
        const formData = new FormData();
        formData.append('kind', 'AFTER_PHOTO');
        formData.append('zone_id', defect.zone_id);
        formData.append('defect_id', defect.id);
        formData.append('file', file);
        await uploadInspectionFile(projectId, selectedRoundId, formData);
      }
      await refreshWorkflowData(defect.id);
    } catch (uploadError) {
      setWorkflowError(uploadError.message || 'Failed to upload after photos.');
    } finally {
      setWorkflowBusy(false);
    }
  };

  const handlePrintReport = async ({ report_type, filters }) => {
    if (!projectId || !selectedRoundId || !roleContext.canStaff || printingReport) return;

    try {
      setPrintingReport(true);
      setReportError('');
      await createInspectionReportLog(projectId, selectedRoundId, {
        report_type,
        filters: filters || {},
      });
      await loadReportLogs();
    } catch (printError) {
      setReportError(printError.message || 'Failed to log inspection report print.');
      throw printError;
    } finally {
      setPrintingReport(false);
    }
  };

  return (
    <section className="inspection-workspace">
      <div className="inspection-hero">
        <div>
          <div className="inspection-kicker">
            <ClipboardCheck size={16} />
            Project Inspection
          </div>
          <h2>{projectName || 'Inspection'}</h2>
          <div className="inspection-hero-meta">
            <span>{rounds.length} rounds</span>
            <span>{categories.length} categories</span>
            <span>Target {formatInspectionDate(selectedRound?.target_close_at)}</span>
          </div>
        </div>
        <div className="inspection-hero-score">
          <span>{summary?.readiness_score == null ? '-' : `${Number(summary.readiness_score).toFixed(0)}%`}</span>
          <small>readiness</small>
        </div>
      </div>

      {error ? <div className="inspection-alert danger">{error}</div> : null}

      <InspectionRoundPicker
        rounds={rounds}
        selectedRoundId={selectedRoundId}
        onSelectRound={setSelectedRoundId}
        onRefresh={() => loadRounds()}
        refreshing={loadingRounds}
        createOpen={createOpen}
        onToggleCreate={() => setCreateOpen((current) => !current)}
        createDraft={createDraft}
        onCreateDraftChange={setCreateDraft}
        onCreateRound={handleCreateRound}
        creating={creating}
      />

      {!loadingRounds && !rounds.length ? (
        <section className="inspection-empty-state">
          <ClipboardCheck size={26} />
          <div>
            <h3>No inspection rounds</h3>
            <p>Create the first round for this project.</p>
          </div>
        </section>
      ) : (
        <>
          <div className="inspection-local-tabs" aria-label="Inspection views">
            {LOCAL_VIEWS.map((view) => {
              const Icon = view.icon;
              return (
                <button
                  key={view.value}
                  type="button"
                  className={activeView === view.value ? 'active' : ''}
                  onClick={() => setActiveView(view.value)}
                >
                  <Icon size={16} />
                  {view.label}
                </button>
              );
            })}
          </div>

          {summaryError ? <div className="inspection-alert danger">{summaryError}</div> : null}

          {activeView === 'overview' ? (
            <InspectionOverview summary={summary} loading={loadingSummary || loadingRounds} />
          ) : activeView === 'map' ? (
            <>
              {mapError ? <div className="inspection-alert danger">{mapError}</div> : null}
              <InspectionMap
                zones={zones}
                defects={defects}
                selectedZoneId={selectedZoneId}
                selectedDefectId={selectedDefectId}
                draftCoordinate={draftCoordinate}
                loading={loadingInspectionData}
                creatingZone={creatingZone}
                uploadingPlan={uploadingPlan}
                roleContext={roleContext}
                onSelectZone={handleSelectZone}
                onSelectDefect={handleSelectDefect}
                onCreateZone={handleCreateZone}
                onUploadPlan={handleUploadPlan}
                onStartDefect={handleStartDefect}
              />
              <InspectionDefectDrawer
                mode={draftCoordinate ? 'create' : selectedDefect ? 'detail' : ''}
                defect={selectedDefect}
                zones={zones}
                categories={categories}
                subcontractors={subcontractors}
                coordinate={draftCoordinate}
                defaultZoneId={selectedZoneId}
                roleContext={roleContext}
                events={defectEvents}
                loadingEvents={loadingEvents}
                workflowBusy={workflowBusy}
                workflowError={workflowError}
                onClose={handleCloseDrawer}
                onCreateDefect={handleCreateDefect}
                onStatusChange={handleStatusChange}
                onAddComment={handleAddComment}
                onUploadAfterPhotos={handleUploadAfterPhotos}
                saving={savingDefect}
              />
            </>
          ) : activeView === 'register' ? (
            <>
              {mapError ? <div className="inspection-alert danger">{mapError}</div> : null}
              <InspectionDefectTable
                defects={defects}
                zones={zones}
                categories={categories}
                loading={loadingInspectionData}
                onOpenDefect={handleSelectDefect}
                onRefresh={() => loadInspectionData()}
              />
              <InspectionDefectDrawer
                mode={selectedDefect ? 'detail' : ''}
                defect={selectedDefect}
                zones={zones}
                categories={categories}
                subcontractors={subcontractors}
                defaultZoneId={selectedZoneId}
                roleContext={roleContext}
                events={defectEvents}
                loadingEvents={loadingEvents}
                workflowBusy={workflowBusy}
                workflowError={workflowError}
                onClose={handleCloseDrawer}
                onCreateDefect={handleCreateDefect}
                onStatusChange={handleStatusChange}
                onAddComment={handleAddComment}
                onUploadAfterPhotos={handleUploadAfterPhotos}
                saving={savingDefect}
              />
            </>
          ) : activeView === 'reports' ? (
            <InspectionReportView
              projectName={projectName}
              round={selectedRound}
              summary={summary}
              defects={defects}
              zones={zones}
              subcontractors={subcontractors}
              reportLogs={reportLogs}
              loadingLogs={loadingReportLogs}
              canPrint={roleContext.canStaff}
              printing={printingReport}
              printError={reportError}
              onPrintReport={handlePrintReport}
              onRefreshLogs={loadReportLogs}
            />
          ) : (
            <InspectionPlaceholder view={activeView} />
          )}
        </>
      )}
    </section>
  );
}
