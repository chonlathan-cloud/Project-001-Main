import React from 'react';
import { Building2, Cloud, Database, Headphones, LineChart, ShieldCheck } from 'lucide-react';

const supportItems = [
  {
    icon: Database,
    title: 'Backend API',
    status: 'Connected',
    description: 'Core project, BOQ, approval, insight, and profile services.',
  },
  {
    icon: Cloud,
    title: 'Private Storage',
    status: 'Signed URL',
    description: 'KYC, receipt, and profile image assets remain private.',
  },
  {
    icon: LineChart,
    title: 'BOQ Sync',
    status: 'Google Sheets',
    description: 'Project BOQ import jobs are queued and monitored from Projects.',
  },
  {
    icon: ShieldCheck,
    title: 'Authentication',
    status: 'Google / LINE',
    description: 'Admin users sign in with Google and subcontractors use LINE LIFF.',
  },
];

function SupportPage() {
  return (
    <div style={{ maxWidth: '1120px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', gap: '20px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '32px', lineHeight: 1.2, margin: 0, color: 'var(--text-main)' }}>
            Support
          </h1>
          <p style={{ margin: '8px 0 0', color: 'var(--text-muted)', lineHeight: 1.6, maxWidth: '680px' }}>
            Operational status and support references for the RAYADEE admin portal.
          </p>
        </div>

        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '10px',
            padding: '10px 14px',
            borderRadius: '8px',
            backgroundColor: 'var(--card-bg)',
            border: '1px solid var(--border-color)',
            color: 'var(--primary)',
            fontWeight: 700,
          }}
        >
          <Headphones size={18} />
          Internal Support
        </div>
      </header>

      <section
        style={{
          backgroundColor: 'var(--card-bg)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '24px',
          display: 'grid',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              backgroundColor: 'rgba(79, 111, 100, 0.12)',
              color: 'var(--primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Building2 size={20} />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '20px', color: 'var(--text-main)' }}>System References</h2>
            <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
              Read-only status cards, aligned with the Stitch Settings / Integrations guidance.
            </p>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
          {supportItems.map((item) => {
            const Icon = item.icon;
            return (
              <div
                key={item.title}
                style={{
                  border: '1px solid var(--border-color)',
                  borderRadius: '12px',
                  padding: '18px',
                  backgroundColor: 'var(--bg-primary)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'flex-start' }}>
                  <Icon size={20} color="var(--primary)" />
                  <span
                    style={{
                      borderRadius: '999px',
                      backgroundColor: 'rgba(79, 111, 100, 0.12)',
                      color: 'var(--primary)',
                      fontSize: '11px',
                      fontWeight: 700,
                      padding: '5px 8px',
                      textTransform: 'uppercase',
                    }}
                  >
                    {item.status}
                  </span>
                </div>
                <h3 style={{ margin: '14px 0 6px', fontSize: '16px', color: 'var(--text-main)' }}>{item.title}</h3>
                <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.6, color: 'var(--text-muted)' }}>
                  {item.description}
                </p>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

export default SupportPage;
