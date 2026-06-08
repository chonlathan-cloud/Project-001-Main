import React, { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

const currencyFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactCurrencyFormatter = new Intl.NumberFormat('en-US', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

const baseChartTooltipStyle = {
  borderRadius: '14px',
  border: '1px solid #e5e7eb',
  boxShadow: 'none',
};

const budgetCompareSeries = [
  { key: 'customerTotalBudget', label: 'Customer BOQ', color: '#1f2937' },
  { key: 'subcontractorTotalBudget', label: 'Subcontractor BOQ', color: '#c4a470' },
];

const materialMixSeries = [
  { key: 'customerMaterialBudget', label: 'Customer Material', color: '#4f6f64', stackId: 'customer' },
  { key: 'customerLaborBudget', label: 'Customer Labor', color: '#243f36', stackId: 'customer' },
  { key: 'subcontractorMaterialBudget', label: 'Subcontractor Material', color: '#dfc391', stackId: 'sub' },
  { key: 'subcontractorLaborBudget', label: 'Subcontractor Labor', color: '#705b32', stackId: 'sub' },
];

const formatCurrency = (value) => `${currencyFormatter.format(Number(value || 0))} THB`;

const toNumber = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
};

const normalizeSheetName = (value) => {
  const cleaned = String(value || '').trim();
  return cleaned || 'Unassigned';
};

const shortenLabel = (value, maxLength = 18) => {
  const cleaned = String(value || '').trim();
  if (!cleaned) return '-';
  if (cleaned.length <= maxLength) return cleaned;
  return `${cleaned.slice(0, maxLength - 1)}…`;
};

const buildSheetSummary = (wbsSummary = []) => {
  const grouped = new Map();

  wbsSummary.forEach((item) => {
    const sheetName = normalizeSheetName(item?.sheetName);
    const sheetKey = sheetName.toLocaleLowerCase();

    if (!grouped.has(sheetKey)) {
      grouped.set(sheetKey, {
        key: sheetKey,
        sheetName,
        customerTotalBudget: 0,
        subcontractorTotalBudget: 0,
        variance: 0,
        customerMaterialBudget: 0,
        customerLaborBudget: 0,
        subcontractorMaterialBudget: 0,
        subcontractorLaborBudget: 0,
        wbsCount: 0,
      });
    }

    const sheet = grouped.get(sheetKey);
    sheet.customerTotalBudget += toNumber(item?.customerTotalBudget);
    sheet.subcontractorTotalBudget += toNumber(item?.subcontractorTotalBudget);
    sheet.variance += toNumber(item?.variance);
    sheet.customerMaterialBudget += toNumber(item?.customerMaterialBudget);
    sheet.customerLaborBudget += toNumber(item?.customerLaborBudget);
    sheet.subcontractorMaterialBudget += toNumber(item?.subcontractorMaterialBudget);
    sheet.subcontractorLaborBudget += toNumber(item?.subcontractorLaborBudget);
    sheet.wbsCount += 1;
  });

  return Array.from(grouped.values()).map((sheet) => ({
    ...sheet,
    label: shortenLabel(sheet.sheetName),
    fullLabel: sheet.sheetName,
    marginPercent: sheet.customerTotalBudget
      ? (sheet.variance / sheet.customerTotalBudget) * 100
      : null,
    varianceFill: sheet.variance >= 0 ? '#22c55e' : '#ef4444',
  }));
};

function ChartCard({ title, description, children }) {
  return (
    <div
      className="card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        minHeight: '360px',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <h3 style={{ margin: 0, fontSize: '18px' }}>{title}</h3>
        <p style={{ margin: 0, color: '#6b7280', fontSize: '13px', lineHeight: 1.6 }}>
          {description}
        </p>
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>{children}</div>
    </div>
  );
}

function ChartEmptyState({ message }) {
  return (
    <div
      style={{
        height: '100%',
        minHeight: '240px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: '18px',
        backgroundColor: '#fafaf9',
        border: '1px dashed #d6d3d1',
        color: '#6b7280',
        fontSize: '14px',
        textAlign: 'center',
        padding: '20px',
      }}
    >
      {message}
    </div>
  );
}

function ChartLegend({ items }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px 16px', alignItems: 'center' }}>
      {items.map((item) => (
        <div
          key={item.key}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '7px',
            color: '#4b5563',
            fontSize: '12px',
            fontWeight: '700',
          }}
        >
          <span
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '3px',
              backgroundColor: item.color,
              display: 'inline-block',
              flex: '0 0 auto',
            }}
          />
          {item.label}
        </div>
      ))}
    </div>
  );
}

function ChartWithLegend({ items, children }) {
  return (
    <div style={{ height: '100%', minHeight: '260px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <ChartLegend items={items} />
      <div style={{ flex: 1, minHeight: '220px' }}>{children}</div>
    </div>
  );
}

const renderSheetXAxis = () => (
  <XAxis
    dataKey="label"
    axisLine={false}
    tickLine={false}
    interval={0}
    angle={-25}
    textAnchor="end"
    height={64}
    tick={{ fontSize: 12, fill: '#6b7280' }}
  />
);

const renderCurrencyYAxis = () => (
  <YAxis
    axisLine={false}
    tickLine={false}
    tick={{ fontSize: 12, fill: '#6b7280' }}
    tickFormatter={(value) => compactCurrencyFormatter.format(Number(value || 0))}
  />
);

function BoqSheetCharts({ wbsSummary = [] }) {
  const sheetSummary = useMemo(() => buildSheetSummary(wbsSummary), [wbsSummary]);
  const budgetCompareLabelByKey = useMemo(
    () => Object.fromEntries(budgetCompareSeries.map((item) => [item.key, item.label])),
    []
  );
  const materialMixLabelByKey = useMemo(
    () => Object.fromEntries(materialMixSeries.map((item) => [item.key, item.label])),
    []
  );

  return (
    <>
      <ChartCard
        title="Variance by Sheet"
        description="สรุปส่วนต่างระหว่าง Customer BOQ และ Subcontractor BOQ ตาม sheet เพื่อเห็นภาพรวมระดับเอกสารได้เร็วขึ้น"
      >
        {sheetSummary.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sheetSummary} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
              <CartesianGrid stroke="#efe8dc" strokeDasharray="3 3" />
              {renderSheetXAxis()}
              {renderCurrencyYAxis()}
              <Tooltip
                formatter={(value) => [formatCurrency(value), 'Variance']}
                labelFormatter={(_, payload) => payload?.[0]?.payload?.fullLabel || '-'}
                contentStyle={baseChartTooltipStyle}
              />
              <Bar dataKey="variance" radius={[8, 8, 0, 0]}>
                {sheetSummary.map((entry) => (
                  <Cell key={entry.key} fill={entry.varianceFill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <ChartEmptyState message="ยังไม่มี compare summary ระดับ sheet สำหรับสร้างกราฟ variance" />
        )}
      </ChartCard>

      <ChartCard
        title="Customer vs Subcontractor by Sheet"
        description="เทียบงบรวมของทั้งสองฝั่งในแต่ละ sheet เพื่อดู gap ระดับเอกสารแทนการอ่านทีละ WBS"
      >
        {sheetSummary.length ? (
          <ChartWithLegend items={budgetCompareSeries}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sheetSummary} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                <CartesianGrid stroke="#efe8dc" strokeDasharray="3 3" />
                {renderSheetXAxis()}
                {renderCurrencyYAxis()}
                <Tooltip
                  formatter={(value, _name, item) => [
                    formatCurrency(value),
                    budgetCompareLabelByKey[item?.dataKey] || item?.name || '-',
                  ]}
                  labelFormatter={(_, payload) => payload?.[0]?.payload?.fullLabel || '-'}
                  contentStyle={baseChartTooltipStyle}
                />
                {budgetCompareSeries.map((item) => (
                  <Bar
                    key={item.key}
                    dataKey={item.key}
                    name={item.label}
                    fill={item.color}
                    radius={[8, 8, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </ChartWithLegend>
        ) : (
          <ChartEmptyState message="ยังไม่มีข้อมูล sheet summary สำหรับเทียบ Customer และ Subcontractor" />
        )}
      </ChartCard>

      <ChartCard
        title="Material / Labor Mix by Sheet"
        description="รวม Material และ Labor ของ Customer/Subcontractor ตาม sheet เพื่อเห็นโครงสร้างต้นทุนระดับเอกสาร"
      >
        {sheetSummary.length ? (
          <ChartWithLegend items={materialMixSeries}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sheetSummary} margin={{ top: 10, right: 10, left: 0, bottom: 10 }}>
                <CartesianGrid stroke="#efe8dc" strokeDasharray="3 3" />
                {renderSheetXAxis()}
                {renderCurrencyYAxis()}
                <Tooltip
                  formatter={(value, _name, item) => [
                    formatCurrency(value),
                    materialMixLabelByKey[item?.dataKey] || item?.name || '-',
                  ]}
                  labelFormatter={(_, payload) => payload?.[0]?.payload?.fullLabel || '-'}
                  contentStyle={baseChartTooltipStyle}
                />
                {materialMixSeries.map((item) => (
                  <Bar
                    key={item.key}
                    dataKey={item.key}
                    name={item.label}
                    stackId={item.stackId}
                    fill={item.color}
                    radius={[8, 8, 0, 0]}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </ChartWithLegend>
        ) : (
          <ChartEmptyState message="ยังไม่มีข้อมูล material/labor ระดับ sheet สำหรับแสดงผล" />
        )}
      </ChartCard>
    </>
  );
}

export default BoqSheetCharts;
