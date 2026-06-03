import React from 'react';

function DashboardPanel({ title, description, action, className = '', children }) {
  return (
    <section className={`dashboard-panel ${className}`.trim()}>
      <div className="dashboard-panel-header">
        <div>
          <h2>{title}</h2>
          {description ? <p>{description}</p> : null}
        </div>
        {action ? <div className="dashboard-panel-action">{action}</div> : null}
      </div>
      {children}
    </section>
  );
}

export default DashboardPanel;
