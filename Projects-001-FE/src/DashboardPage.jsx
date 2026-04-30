import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Clock3,
  TrendingDown,
  TrendingUp,
  Wallet,
} from 'lucide-react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getDashboardData } from './api';
import Loading from './components/Loading';

const currencyFormatter = new Intl.NumberFormat('th-TH', {
  style: 'currency',
  currency: 'THB',
  maximumFractionDigits: 0,
});

const numberFormatter = new Intl.NumberFormat('th-TH');

const percentFormatter = new Intl.NumberFormat('th-TH', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const toneStyles = {
  neutral: {
    background: '#ffffff',
    border: '#e7e0d4',
    text: '#1f2937',
    subtle: '#6b7280',
    accent: '#c4a470',
  },
  positive: {
    background: '#f3fbf7',
    border: '#b6e3ca',
    text: '#166534',
    subtle: '#2f855a',
    accent: '#27a57a',
  },
  warning: {
    background: '#fff8ec',
    border: '#f1d19a',
    text: '#9a6700',
    subtle: '#b7791f',
    accent: '#d0a24c',
  },
  danger: {
    background: '#fef2f2',
    border: '#f0b6b6',
    text: '#9f1239',
    subtle: '#be123c',
    accent: '#de5b52',
  },
};

const sectionTitleStyle = {
  fontSize: '20px',
  fontWeight: '700',
  color: '#1f2937',
};

const sectionDescriptionStyle = {
  fontSize: '13px',
  lineHeight: 1.6,
  color: '#6b7280',
};

function formatMetric(value, kind) {
  if (kind === 'currency') {
    return currencyFormatter.format(Number(value || 0));
  }

  if (kind === 'percent') {
    return `${percentFormatter.format(Number(value || 0))}%`;
  }

  return numberFormatter.format(Number(value || 0));
}

function formatDateTime(value) {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;

  return parsed.toLocaleString('th-TH', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function KpiCard({ card }) {
  const tone = toneStyles[card.tone] || toneStyles.neutral;

  return (
    <div
      className="dashboard-kpi-card"
      style={{
        background: tone.background,
        border: `1px solid ${tone.border}`,
      }}
    >
      <div
        style={{
          width: '42px',
          height: '42px',
          borderRadius: '14px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(255,255,255,0.75)',
          color: tone.accent,
        }}
      >
        {card.kind === 'percent' ? <TrendingUp size={18} /> : <Wallet size={18} />}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <div>
          <div style={{ fontSize: '13px', fontWeight: '700', color: tone.subtle }}>
            {card.label}
          </div>
          <div style={{ marginTop: '8px', fontSize: '29px', fontWeight: '800', color: tone.text }}>
            {formatMetric(card.value, card.kind)}
          </div>
        </div>

        <div style={{ fontSize: '12px', lineHeight: 1.6, color: tone.subtle }}>
          {card.description}
        </div>
      </div>
    </div>
  );
}

function BudgetRow({ item }) {
  const tone = toneStyles[item.tone] || toneStyles.neutral;

  return (
    <div
      style={{
        padding: '16px 18px',
        borderRadius: '16px',
        background: tone.background,
        border: `1px solid ${tone.border}`,
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ fontSize: '14px', fontWeight: '700', color: tone.text }}>{item.label}</div>
        <div style={{ fontSize: '13px', fontWeight: '700', color: tone.text }}>
          {formatMetric(item.value, 'currency')}
        </div>
      </div>

      <div
        style={{
          width: '100%',
          height: '10px',
          borderRadius: '999px',
          background: '#ede8df',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${Math.max(0, Math.min(Number(item.ratio || 0), 100))}%`,
            height: '100%',
            borderRadius: '999px',
            background: tone.accent,
          }}
        />
      </div>

      <div style={{ fontSize: '12px', color: tone.subtle }}>
        {percentFormatter.format(Number(item.ratio || 0))}% ของงบรวม
      </div>
    </div>
  );
}

function AttentionItem({ item }) {
  const tone = toneStyles[item.tone] || toneStyles.neutral;

  return (
    <div
      style={{
        padding: '16px 18px',
        borderRadius: '16px',
        border: `1px solid ${tone.border}`,
        background: tone.background,
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
        <div style={{ fontSize: '14px', fontWeight: '700', color: tone.text }}>{item.label}</div>
        <div style={{ fontSize: '16px', fontWeight: '800', color: tone.text }}>
          {formatMetric(item.value, item.kind)}
        </div>
      </div>
      <div style={{ fontSize: '12px', lineHeight: 1.6, color: tone.subtle }}>{item.description}</div>
    </div>
  );
}

function DashboardPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError('');
        const result = await getDashboardData();
        setData(result);
      } catch (loadError) {
        setError(loadError.message || 'Failed to load dashboard data.');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) return <Loading />;

  if (error) {
    return (
      <div className="card" style={{ backgroundColor: 'white', color: '#de5b52' }}>
        {error}
      </div>
    );
  }

  const latestMonth = data?.cashflow?.[data.cashflow.length - 1] || null;
  const utilizationTone = (data?.kpis?.budgetUtilization || 0) > 85 ? toneStyles.warning : toneStyles.positive;
  const cashflowIsNegative = (data?.kpis?.netCashflow || 0) < 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <section
        className="dashboard-hero"
        style={{
          background:
            'linear-gradient(135deg, rgba(61,64,58,1) 0%, rgba(92,97,86,1) 46%, rgba(196,164,112,0.92) 100%)',
          color: 'white',
          borderRadius: '28px',
          padding: '28px',
          boxShadow: '0 24px 60px rgba(49, 46, 38, 0.18)',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              borderRadius: '999px',
              background: 'rgba(255,255,255,0.14)',
              fontSize: '12px',
              fontWeight: '700',
              width: 'fit-content',
            }}
          >
            <Clock3 size={14} />
            Live summary from project, installment, transaction, and input request data
          </div>

          <div>
            <h1 style={{ fontSize: '34px', lineHeight: 1.15, marginBottom: '10px' }}>
              Dashboard ที่ควรตอบคำถามว่าเงินอยู่ตรงไหน และงานติดตรงไหน
            </h1>
            <p style={{ maxWidth: '720px', fontSize: '15px', lineHeight: 1.7, color: 'rgba(255,255,255,0.82)' }}>
              หน้าเดิมใช้ชื่อกราฟแบบ generic จนตีความยาก หน้าใหม่นี้เปลี่ยนเป็นภาษาธุรกิจตรง ๆ:
              งบรวม, ต้นทุนจริง, ค้างชำระ, cashflow และกิจกรรมล่าสุด
            </p>
          </div>
        </div>

        <div className="dashboard-hero-metrics">
          <div
            style={{
              borderRadius: '22px',
              padding: '20px',
              background: 'rgba(255,255,255,0.12)',
              border: '1px solid rgba(255,255,255,0.15)',
              backdropFilter: 'blur(6px)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              {cashflowIsNegative ? <TrendingDown size={18} /> : <TrendingUp size={18} />}
              <span style={{ fontSize: '13px', fontWeight: '700' }}>Net Cashflow</span>
            </div>
            <div style={{ fontSize: '30px', fontWeight: '800' }}>
              {formatMetric(data?.kpis?.netCashflow, 'currency')}
            </div>
            <div style={{ marginTop: '8px', fontSize: '12px', color: 'rgba(255,255,255,0.8)' }}>
              รายรับรวม {formatMetric(data?.kpis?.totalIncome, 'currency')} เทียบกับรายจ่ายรวม{' '}
              {formatMetric(data?.kpis?.totalExpense, 'currency')}
            </div>
          </div>

          <div
            style={{
              borderRadius: '22px',
              padding: '20px',
              background: 'rgba(255,255,255,0.12)',
              border: '1px solid rgba(255,255,255,0.15)',
              backdropFilter: 'blur(6px)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <AlertTriangle size={18} />
              <span style={{ fontSize: '13px', fontWeight: '700' }}>Budget Utilization</span>
            </div>
            <div style={{ fontSize: '30px', fontWeight: '800' }}>
              {formatMetric(data?.kpis?.budgetUtilization, 'percent')}
            </div>
            <div style={{ marginTop: '8px', fontSize: '12px', color: 'rgba(255,255,255,0.8)' }}>
              งบคงเหลือ {formatMetric(data?.kpis?.remainingBudget, 'currency')}
            </div>
          </div>

          <div
            style={{
              borderRadius: '22px',
              padding: '20px',
              background: 'rgba(255,255,255,0.12)',
              border: '1px solid rgba(255,255,255,0.15)',
              backdropFilter: 'blur(6px)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
              <Clock3 size={18} />
              <span style={{ fontSize: '13px', fontWeight: '700' }}>Latest Period</span>
            </div>
            <div style={{ fontSize: '30px', fontWeight: '800' }}>
              {latestMonth?.month || '-'}
            </div>
            <div style={{ marginTop: '8px', fontSize: '12px', color: 'rgba(255,255,255,0.8)' }}>
              ล่าสุดรับ {formatMetric(latestMonth?.income, 'currency')} จ่าย{' '}
              {formatMetric(latestMonth?.expense, 'currency')}
            </div>
          </div>
        </div>
      </section>

      <section className="dashboard-kpi-grid">
        {data?.statCards?.map((card) => (
          <KpiCard key={card.key} card={card} />
        ))}
      </section>

      <section className="dashboard-main-grid">
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={sectionTitleStyle}>Monthly Cashflow</div>
            <div style={sectionDescriptionStyle}>
              เปรียบเทียบรายรับจาก installments กับรายจ่ายที่อนุมัติแล้วในแต่ละเดือน
            </div>
          </div>

          <div style={{ height: '340px' }}>
            {data?.cashflow?.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={data.cashflow} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid stroke="#efe8dc" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="month"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: '#6b7280' }}
                  />
                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 12, fill: '#6b7280' }}
                    tickFormatter={(value) => `${Math.round(Number(value || 0) / 1000)}k`}
                  />
                  <Tooltip
                    formatter={(value, name) => [
                      formatMetric(value, 'currency'),
                      name === 'income' ? 'Income' : name === 'expense' ? 'Expense' : 'Balance',
                    ]}
                    labelStyle={{ color: '#111827', fontWeight: 700 }}
                    contentStyle={{
                      borderRadius: '14px',
                      border: '1px solid #e5e7eb',
                      boxShadow: '0 18px 40px rgba(15, 23, 42, 0.08)',
                    }}
                  />
                  <Bar dataKey="income" name="income" fill="#27a57a" radius={[8, 8, 0, 0]} barSize={26} />
                  <Bar dataKey="expense" name="expense" fill="#de5b52" radius={[8, 8, 0, 0]} barSize={18} />
                  <Line
                    type="monotone"
                    dataKey="balance"
                    name="balance"
                    stroke="#3d403a"
                    strokeWidth={3}
                    dot={{ r: 4, strokeWidth: 0, fill: '#3d403a' }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <div
                style={{
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  borderRadius: '18px',
                  background: '#faf7f2',
                  color: '#6b7280',
                  fontSize: '14px',
                }}
              >
                ยังไม่มีข้อมูล cashflow สำหรับแสดงผล
              </div>
            )}
          </div>
        </div>

        <div className="dashboard-side-stack">
          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={sectionTitleStyle}>Budget Health</div>
              <div style={sectionDescriptionStyle}>
                สัดส่วนการใช้งบและจุดเสี่ยงที่ควรจับตาในภาพรวม
              </div>
            </div>

            <div
              style={{
                borderRadius: '18px',
                padding: '18px',
                background: utilizationTone.background,
                border: `1px solid ${utilizationTone.border}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px',
              }}
            >
              <div>
                <div style={{ fontSize: '12px', fontWeight: '700', color: utilizationTone.subtle }}>
                  Spending status
                </div>
                <div style={{ marginTop: '8px', fontSize: '26px', fontWeight: '800', color: utilizationTone.text }}>
                  {formatMetric(data?.kpis?.budgetUtilization, 'percent')}
                </div>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  color: utilizationTone.text,
                  fontSize: '13px',
                  fontWeight: '700',
                }}
              >
                {(data?.kpis?.budgetUtilization || 0) > 85 ? <ArrowUpRight size={18} /> : <ArrowDownRight size={18} />}
                {(data?.kpis?.budgetUtilization || 0) > 85 ? 'ควรตรวจสอบงบใกล้เต็ม' : 'ยังอยู่ในกรอบใช้งบ'}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {data?.budgetBreakdown?.map((item) => (
                <BudgetRow key={item.key} item={item} />
              ))}
            </div>
          </div>

          <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={sectionTitleStyle}>Attention Today</div>
              <div style={sectionDescriptionStyle}>
                จุดที่ควรเปิดไปจัดการต่อทันทีจากข้อมูล summary ชุดนี้
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {data?.attentionItems?.map((item) => (
                <AttentionItem key={item.key} item={item} />
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="dashboard-bottom-grid">
        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={sectionTitleStyle}>Recent Actions</div>
            <div style={sectionDescriptionStyle}>
              เหตุการณ์ล่าสุดจากการอนุมัติ transaction และ input request
            </div>
          </div>

          <div className="dashboard-timeline">
            {data?.recentActions?.length ? (
              data.recentActions.map((item, index) => (
                <div key={item.id} className="dashboard-timeline-item">
                  <div
                    style={{
                      width: '12px',
                      height: '12px',
                      borderRadius: '999px',
                      background: index === 0 ? '#27a57a' : '#c4a470',
                      marginTop: '6px',
                      flexShrink: 0,
                    }}
                  />

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ fontSize: '12px', fontWeight: '700', color: '#8b7355' }}>
                      {formatDateTime(item.time)}
                    </div>
                    <div style={{ fontSize: '14px', lineHeight: 1.7, color: '#1f2937' }}>
                      {item.action || '-'}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div
                style={{
                  padding: '18px',
                  borderRadius: '16px',
                  background: '#faf7f2',
                  color: '#6b7280',
                  fontSize: '14px',
                }}
              >
                ยังไม่มีกิจกรรมล่าสุดให้แสดง
              </div>
            )}
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={sectionTitleStyle}>What This Dashboard Means</div>
            <div style={sectionDescriptionStyle}>
              หากต้องการให้หน้า dashboard ชัดขึ้นกว่าเดิม ควรตอบ 3 คำถามนี้ให้ได้ใน 5 วินาที
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {[
              {
                title: 'เรามีงบเหลือเท่าไร',
                detail: `ตอนนี้งบคงเหลือ ${formatMetric(data?.kpis?.remainingBudget, 'currency')} จากงบรวม ${formatMetric(data?.kpis?.totalBudget, 'currency')}`,
              },
              {
                title: 'เงินเข้าออกสมดุลไหม',
                detail: `Net cashflow ปัจจุบันอยู่ที่ ${formatMetric(data?.kpis?.netCashflow, 'currency')}`,
              },
              {
                title: 'มีอะไรติดค้างต้องรีบเคลียร์',
                detail: `มี ${formatMetric(data?.kpis?.pendingApprovalCount, 'number')} รายการรออนุมัติ และยอดค้างชำระ ${formatMetric(data?.kpis?.overdueAmount, 'currency')}`,
              },
            ].map((item) => (
              <div
                key={item.title}
                style={{
                  padding: '16px 18px',
                  borderRadius: '16px',
                  background: '#faf7f2',
                  border: '1px solid #eee5d7',
                }}
              >
                <div style={{ fontSize: '14px', fontWeight: '700', color: '#1f2937' }}>{item.title}</div>
                <div style={{ marginTop: '8px', fontSize: '13px', lineHeight: 1.7, color: '#6b7280' }}>
                  {item.detail}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

export default DashboardPage;
