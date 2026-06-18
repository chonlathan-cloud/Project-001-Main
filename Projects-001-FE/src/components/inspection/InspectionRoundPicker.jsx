import { CalendarDays, ChevronDown, Plus, RefreshCw } from 'lucide-react';
import { formatInspectionDate, getRoundStatusLabel } from './inspectionUtils';

function RoundOptionMeta({ round }) {
  if (!round) return null;

  return (
    <div className="inspection-round-meta">
      <span>{getRoundStatusLabel(round.status)}</span>
      <span>Started {formatInspectionDate(round.started_at)}</span>
      <span>Target {formatInspectionDate(round.target_close_at)}</span>
    </div>
  );
}

export default function InspectionRoundPicker({
  rounds,
  selectedRoundId,
  onSelectRound,
  onRefresh,
  refreshing = false,
  createOpen = false,
  onToggleCreate,
  createDraft,
  onCreateDraftChange,
  onCreateRound,
  creating = false,
}) {
  const selectedRound = rounds.find((round) => round.id === selectedRoundId) || null;

  return (
    <section className="inspection-round-panel">
      <div className="inspection-round-picker">
        <div className="inspection-round-select-wrap">
          <label htmlFor="inspection-round-select">Inspection round</label>
          <div className="inspection-select-shell">
            <select
              id="inspection-round-select"
              value={selectedRoundId || ''}
              onChange={(event) => onSelectRound(event.target.value)}
              disabled={!rounds.length}
            >
              {rounds.length ? null : <option value="">No rounds</option>}
              {rounds.map((round) => (
                <option key={round.id} value={round.id}>
                  {round.name}
                </option>
              ))}
            </select>
            <ChevronDown size={16} />
          </div>
          <RoundOptionMeta round={selectedRound} />
        </div>

        <div className="inspection-round-actions">
          <button type="button" className="inspection-button secondary" onClick={onRefresh} disabled={refreshing}>
            <RefreshCw size={16} />
            Refresh
          </button>
          <button type="button" className="inspection-button primary" onClick={onToggleCreate}>
            <Plus size={16} />
            New Round
          </button>
        </div>
      </div>

      {createOpen ? (
        <form className="inspection-create-round" onSubmit={onCreateRound}>
          <label>
            Round name
            <input
              value={createDraft.name}
              onChange={(event) => onCreateDraftChange({ ...createDraft, name: event.target.value })}
              placeholder="Pre-handover Round 1"
              required
            />
          </label>
          <label>
            Target close date
            <span className="inspection-date-input">
              <CalendarDays size={16} />
              <input
                value={createDraft.targetCloseDate}
                onChange={(event) => onCreateDraftChange({ ...createDraft, targetCloseDate: event.target.value })}
                type="date"
              />
            </span>
          </label>
          <label className="inspection-create-round-description">
            Description
            <input
              value={createDraft.description}
              onChange={(event) => onCreateDraftChange({ ...createDraft, description: event.target.value })}
              placeholder="Inspection before handover"
            />
          </label>
          <div className="inspection-create-round-actions">
            <button type="button" className="inspection-button secondary" onClick={onToggleCreate}>
              Cancel
            </button>
            <button type="submit" className="inspection-button primary" disabled={creating}>
              <Plus size={16} />
              Create
            </button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
