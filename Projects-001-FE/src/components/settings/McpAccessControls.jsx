import { ShieldCheck, Unplug } from 'lucide-react';
import { SettingsBadge, SettingsToggle } from '../SettingsWorkspace';

const MCP_PERMISSION_OPTIONS = [
  {
    id: 'mcp_access',
    label: 'External MCP access',
    description: 'Required for an Admin to connect an approved external MCP client.',
  },
  {
    id: 'financial_data_read',
    label: 'Finance & insights',
    description: 'Read exact financial summaries, payments, dashboard facts, and insights.',
  },
  {
    id: 'sensitive_documents_read',
    label: 'Sensitive documents',
    description: 'Read bounded existing extraction through the Document Gateway.',
  },
  {
    id: 'infrastructure_read',
    label: 'GCP operations',
    description: 'Read curated health, Cloud Run, error, and processing status only.',
  },
  {
    id: 'audit_log_read',
    label: 'Product audit',
    description: 'Read allowlisted Product MCP audit metadata from the dedicated view.',
  },
];

function McpAccessControls({
  form,
  disabled,
  isOwnerRole,
  onFieldChange,
  onPermissionToggle,
  onRevoke,
}) {
  const permissions = Array.isArray(form.mcp_permissions) ? form.mcp_permissions : [];
  const isBound = Boolean(form.mcp_oauth_issuer && form.mcp_oauth_subject);

  return (
    <section className="settings-mcp-card" aria-labelledby="mcp-access-heading">
      <header className="settings-mcp-header">
        <span className="settings-integration-icon" aria-hidden="true">
          <ShieldCheck size={19} strokeWidth={2.2} />
        </span>
        <div>
          <span className="settings-kicker">External AI Data Boundary</span>
          <h4 id="mcp-access-heading">Product MCP access</h4>
          <p>
            Owner-managed, read-only access. Every call rechecks the account, permissions,
            and assigned projects in the Product Backend.
          </p>
        </div>
        <SettingsBadge tone={form.external_mcp_enabled ? 'success' : 'neutral'}>
          {form.external_mcp_enabled ? 'Enabled' : 'Disabled'}
        </SettingsBadge>
      </header>

      <div className="settings-row-stack">
        <SettingsToggle
          checked={Boolean(form.external_mcp_enabled)}
          disabled={disabled}
          label="Allow external MCP connection"
          description="Requires an exact OAuth issuer and subject binding. Disabling takes effect on the next tool call."
          onChange={(checked) => onFieldChange('external_mcp_enabled', checked)}
        />
        {!isOwnerRole ? (
          <SettingsToggle
            checked={Boolean(form.mcp_all_projects_read)}
            disabled={disabled}
            label="Allow all projects"
            description="When off, MCP reads are restricted to the assigned project list above."
            onChange={(checked) => onFieldChange('mcp_all_projects_read', checked)}
          />
        ) : null}
      </div>

      <div className="settings-form-grid two">
        <label className="settings-field">
          <span>OAuth Issuer</span>
          <input
            className="settings-input"
            inputMode="url"
            autoComplete="off"
            placeholder="https://issuer.example.com"
            value={form.mcp_oauth_issuer}
            onChange={(event) => onFieldChange('mcp_oauth_issuer', event.target.value)}
            disabled={disabled}
          />
        </label>
        <label className="settings-field">
          <span>OAuth Subject</span>
          <input
            className="settings-input"
            autoComplete="off"
            placeholder="Stable subject identifier"
            value={form.mcp_oauth_subject}
            onChange={(event) => onFieldChange('mcp_oauth_subject', event.target.value)}
            disabled={disabled}
          />
        </label>
      </div>

      <div className="settings-mcp-permissions">
        <div>
          <span className="settings-kicker">Additional Permissions</span>
          <strong>
            {isOwnerRole ? 'Owner has implicit full read access' : `${permissions.length} selected`}
          </strong>
        </div>
        <div className="settings-mcp-permission-grid">
          {MCP_PERMISSION_OPTIONS.map((permission) => {
            const checked = permissions.includes(permission.id);
            return (
              <label key={permission.id} className={checked ? 'selected' : ''}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onPermissionToggle(permission.id)}
                  disabled={disabled || isOwnerRole}
                />
                <span>
                  <strong>{permission.label}</strong>
                  <small>{permission.description}</small>
                </span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="settings-mcp-footer">
        <p>
          External AI clients may retain delivered content under their own terms. Product MCP
          never returns tokens, signed URLs, storage paths, prompts, or full response bodies in logs.
        </p>
        <button
          type="button"
          className="settings-button danger"
          onClick={onRevoke}
          disabled={disabled || (!form.external_mcp_enabled && !isBound && permissions.length === 0)}
        >
          <Unplug size={16} />
          Revoke &amp; unbind
        </button>
      </div>
    </section>
  );
}

export default McpAccessControls;
