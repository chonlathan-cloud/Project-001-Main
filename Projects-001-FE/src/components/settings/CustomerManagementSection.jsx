import React from 'react';
import { Copy, Link2Off, LoaderCircle, Save } from 'lucide-react';

import {
  SettingsAccordionItem,
  SettingsAvatar,
  SettingsBadge,
  SettingsDetailGrid,
  SettingsPanelHeader,
} from '../SettingsWorkspace';

const displayValue = (value) => {
  const text = String(value ?? '').trim();
  return text || '-';
};

const formatDateTime = (value) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Bangkok',
  }).format(date);
};

const projectIdOf = (project) => String(project.project_id || project.id || '');
const projectNameOf = (project) => project.name || project.project_name || projectIdOf(project);
const customerNameOf = (customer) => {
  const firstName = customer.first_name || customer.contact_name || customer.name || '';
  const nickname = String(customer.nickname || '').trim();
  return `${firstName}${nickname && nickname !== firstName ? ` (${nickname})` : ''}`.trim();
};

const CustomerManagementSection = ({
  canEdit,
  customerForm,
  customers,
  filteredCustomers,
  onCopy,
  onFieldChange,
  onResetLine,
  onSave,
  onSearchChange,
  onSelect,
  onToggleProject,
  projects,
  saving,
  search,
  selectedCustomerId,
}) => {
  const projectNames = new Map(
    projects.map((project) => [projectIdOf(project), projectNameOf(project)]),
  );
  const connectedCount = customers.filter((item) => Boolean(item.line_uid)).length;
  const activeCount = customers.filter((item) => item.is_active !== false).length;

  return (
    <section className="settings-accordion-section" aria-labelledby="customer-management-title">
      <SettingsPanelHeader
        kicker="Customer Access"
        title="Customer Management"
        description="Manage customer LINE accounts, project access, and account status."
        action={(
          <div className="settings-search">
            <input
              value={search}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Search customers"
              aria-label="Search customers"
            />
          </div>
        )}
      />

      <div className="settings-metric-grid">
        <article>
          <span>Total Customers</span>
          <strong>{customers.length.toLocaleString('en-US')}</strong>
        </article>
        <article>
          <span>LINE Connected</span>
          <strong>{connectedCount.toLocaleString('en-US')}</strong>
        </article>
        <article>
          <span>Active Accounts</span>
          <strong>{activeCount.toLocaleString('en-US')}</strong>
        </article>
      </div>

      <div className="settings-accordion-list">
        {filteredCustomers.length > 0 ? (
          filteredCustomers.map((item) => {
            const isOpen = selectedCustomerId === item.id;
            const customerName = customerNameOf(item);
            const assignedProjectIds = Array.isArray(item.assigned_project_ids)
              ? item.assigned_project_ids
              : [];
            const assignedProjectNames = assignedProjectIds
              .map((projectId) => projectNames.get(String(projectId)) || projectId)
              .filter(Boolean)
              .join(', ');

            return (
              <SettingsAccordionItem
                key={item.id}
                id={`customer-${item.id}`}
                isOpen={isOpen}
                onToggle={() => onSelect(isOpen ? '' : item.id)}
                avatar={(
                  <SettingsAvatar
                    name={customerName}
                    imageUrl={item.line_picture_url}
                  />
                )}
                title={customerName || 'Unnamed customer'}
                subtitle={item.nickname ? `ชื่อที่ใช้ในระบบ: ${item.nickname}` : item.name || item.phone || item.id}
                meta={(
                  <>
                    <SettingsBadge tone={item.line_uid ? 'success' : 'warning'}>
                      {item.line_uid ? 'LINE Connected' : 'LINE Pending'}
                    </SettingsBadge>
                    <SettingsBadge tone={item.is_active !== false ? 'success' : 'neutral'}>
                      {item.is_active !== false ? 'Active' : 'Inactive'}
                    </SettingsBadge>
                  </>
                )}
              >
                <div className="settings-accordion-detail">
                  <SettingsDetailGrid
                    items={[
                      { label: 'Customer ID', value: item.id, wide: true },
                      { label: 'First Name', value: displayValue(item.first_name || item.contact_name) },
                      { label: 'Nickname', value: displayValue(item.nickname) },
                      { label: 'Contact Name', value: displayValue(item.contact_name) },
                      { label: 'Display Name', value: displayValue(item.name) },
                      { label: 'Phone', value: displayValue(item.phone) },
                      { label: 'Status', value: item.is_active !== false ? 'Active' : 'Inactive' },
                      { label: 'LINE UID', value: displayValue(item.line_uid), wide: true },
                      { label: 'Assigned Projects', value: displayValue(assignedProjectNames), wide: true },
                      { label: 'Approved On', value: formatDateTime(item.created_at) },
                      { label: 'Last Updated', value: formatDateTime(item.updated_at) },
                    ]}
                  />

                  <div className="settings-inline-editor">
                    <div>
                      <span className="settings-kicker">Customer Access</span>
                      <h4>Edit customer profile and projects</h4>
                    </div>

                    <div className="settings-form-grid two">
                      <label className="settings-field">
                        <span>Display Name</span>
                        <input
                          className="settings-input"
                          value={customerForm.name}
                          onChange={(event) => onFieldChange('name', event.target.value)}
                          disabled={!canEdit}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Contact Name</span>
                        <input
                          className="settings-input"
                          value={customerForm.contact_name}
                          onChange={(event) => onFieldChange('contact_name', event.target.value)}
                          disabled={!canEdit}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Phone</span>
                        <input
                          className="settings-input"
                          type="tel"
                          value={customerForm.phone}
                          onChange={(event) => onFieldChange('phone', event.target.value)}
                          disabled={!canEdit}
                        />
                      </label>
                      <label className="settings-field">
                        <span>Status</span>
                        <select
                          className="settings-input"
                          value={customerForm.is_active ? 'active' : 'inactive'}
                          onChange={(event) => onFieldChange('is_active', event.target.value === 'active')}
                          disabled={!canEdit}
                        >
                          <option value="active">Active</option>
                          <option value="inactive">Inactive</option>
                        </select>
                      </label>
                    </div>

                    <div className="settings-project-assignment">
                      <div>
                        <span className="settings-kicker">Assigned Projects</span>
                        <strong>{customerForm.assigned_project_ids.length} selected</strong>
                      </div>
                      {projects.length === 0 ? (
                        <div className="settings-empty-row">No projects available.</div>
                      ) : (
                        <div className="settings-project-grid">
                          {projects.map((project) => {
                            const projectId = projectIdOf(project);
                            const checked = customerForm.assigned_project_ids.includes(projectId);
                            return (
                              <label key={projectId} className={checked ? 'selected' : ''}>
                                <input
                                  type="checkbox"
                                  checked={checked}
                                  onChange={() => onToggleProject(projectId)}
                                  disabled={!canEdit}
                                />
                                <span>{projectNameOf(project)}</span>
                              </label>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    <div className="settings-editor-actions">
                      <span>
                        {canEdit
                          ? 'Changes affect which published reports this customer can access.'
                          : 'This customer record is read only for your role.'}
                      </span>
                      <div>
                        <button
                          type="button"
                          className="settings-button secondary"
                          onClick={() => onCopy(item)}
                          disabled={saving}
                        >
                          <Copy size={16} />
                          Copy Info
                        </button>
                        <button
                          type="button"
                          className="settings-button danger"
                          onClick={() => onResetLine(item)}
                          disabled={saving || !canEdit || !item.line_uid}
                        >
                          <Link2Off size={16} />
                          Reset LINE
                        </button>
                        <button
                          type="button"
                          className="settings-button primary"
                          onClick={onSave}
                          disabled={saving || !canEdit}
                        >
                          {saving ? <LoaderCircle size={16} className="spin" /> : <Save size={16} />}
                          Save Customer
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </SettingsAccordionItem>
            );
          })
        ) : (
          <div className="settings-empty-state">No customers match this search.</div>
        )}
      </div>
    </section>
  );
};

export default CustomerManagementSection;
