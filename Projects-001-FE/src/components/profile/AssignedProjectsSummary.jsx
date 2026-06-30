import { useMemo } from 'react';
import { Briefcase } from 'lucide-react';

const normalizeId = (value) => String(value || '').trim();

const resolveProjectName = (project = {}) =>
  String(
    project.name ||
      project.project_name ||
      project.projectName ||
      project.title ||
      project.display_name ||
      ''
  ).trim();

export default function AssignedProjectsSummary({
  label,
  projectIds = [],
  projects = [],
  loading = false,
  error = '',
  emptyText = 'ยังไม่มีโครงการที่ได้รับมอบหมาย',
  loadingText = 'กำลังโหลดชื่อโครงการ...',
  unavailableText = 'ยังโหลดชื่อโครงการไม่ได้',
  hiddenCountText = 'ยังไม่มีชื่อแสดง',
}) {
  const normalizedIds = useMemo(
    () => Array.from(new Set(projectIds.map(normalizeId).filter(Boolean))),
    [projectIds]
  );

  const projectEntries = useMemo(() => {
    const nameById = new Map();
    projects.forEach((project) => {
      const projectId = normalizeId(project.project_id || project.id);
      const projectName = resolveProjectName(project);
      if (projectId && projectName) {
        nameById.set(projectId, projectName);
      }
    });

    return normalizedIds
      .map((projectId) => ({
        id: projectId,
        name: nameById.get(projectId),
      }))
      .filter((project) => project.name);
  }, [normalizedIds, projects]);

  const hiddenCount = Math.max(normalizedIds.length - projectEntries.length, 0);
  const shouldShowStatus = !projectEntries.length || hiddenCount > 0 || loading || error;

  let statusText = '';
  if (!normalizedIds.length) {
    statusText = emptyText;
  } else if (loading && !projectEntries.length) {
    statusText = loadingText;
  } else if (error && !projectEntries.length) {
    statusText = `${unavailableText} (${normalizedIds.length} โครงการ)`;
  } else if (!projectEntries.length) {
    statusText = `${hiddenCountText} (${normalizedIds.length} โครงการ)`;
  } else if (hiddenCount > 0) {
    statusText = `${hiddenCount} โครงการ${hiddenCountText}`;
  }

  return (
    <div style={{ display: 'grid', gap: '8px' }}>
      <div style={{ fontSize: '12px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
        {label}
      </div>

      {projectEntries.length ? (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
          {projectEntries.map((project) => (
            <span
              key={project.id}
              style={{
                minHeight: '32px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '7px',
                maxWidth: '100%',
                padding: '7px 10px',
                borderRadius: '999px',
                border: '1px solid rgba(79, 111, 100, 0.22)',
                backgroundColor: 'rgba(79, 111, 100, 0.08)',
                color: 'var(--text-main)',
                fontSize: '13px',
                fontWeight: '700',
                lineHeight: 1.35,
                overflowWrap: 'anywhere',
              }}
            >
              <Briefcase size={14} style={{ color: 'var(--primary)', flex: '0 0 auto' }} />
              <span>{project.name}</span>
            </span>
          ))}
        </div>
      ) : null}

      {shouldShowStatus && statusText ? (
        <div
          style={{
            color: projectEntries.length ? 'var(--text-muted)' : 'var(--text-main)',
            fontSize: '13px',
            fontWeight: projectEntries.length ? '600' : '700',
            lineHeight: 1.5,
          }}
        >
          {statusText}
        </div>
      ) : null}
    </div>
  );
}
