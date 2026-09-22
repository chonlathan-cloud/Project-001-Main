export const DOCUMENT_SCHEMA_VERSION = 'boq-v2-document-snapshot-v2';

export const SECTION_DEFINITIONS = [
  { section_type: 'SUMMARY', title_th: 'สรุปใบเสนอราคา', title_en: 'Quotation Summary', required: true },
  { section_type: 'DETAILED_BOQ', title_th: 'รายละเอียด BOQ', title_en: 'Detailed BOQ', required: true },
  { section_type: 'VISUAL', title_th: 'รูปภาพและรายละเอียดงาน', title_en: 'Visual / Work Detail' },
  { section_type: 'PAYMENT_TERMS', title_th: 'เงื่อนไขการชำระเงิน', title_en: 'Payment Terms' },
  { section_type: 'TERMS', title_th: 'ข้อกำหนดและเงื่อนไข', title_en: 'Terms & Conditions' },
  { section_type: 'ACCEPTANCE', title_th: 'การยอมรับใบเสนอราคา', title_en: 'Acceptance' },
];

const OPTIONAL_DEFAULTS = {
  VISUAL: false,
  PAYMENT_TERMS: true,
  TERMS: true,
  ACCEPTANCE: false,
};

export function defaultDocumentSections(documentPages = []) {
  const legacyPages = new Set(documentPages);
  return SECTION_DEFINITIONS.map((definition, position) => ({
    section_type: definition.section_type,
    enabled: definition.required || (
      definition.section_type === 'PAYMENT_TERMS'
        ? legacyPages.size === 0 || legacyPages.has('PAYMENT_TERMS')
        : definition.section_type === 'TERMS'
          ? legacyPages.size === 0 || legacyPages.has('COMMERCIAL_TERMS')
          : OPTIONAL_DEFAULTS[definition.section_type]
    ),
    position,
    title_th: definition.title_th,
    title_en: definition.title_en,
  }));
}

export function normalizeDocumentSections(sections, documentPages = []) {
  const source = Array.isArray(sections) && sections.length
    ? sections
    : defaultDocumentSections(documentPages);
  const byType = new Map(source.map((section) => [section.section_type, section]));
  const ordered = [...source]
    .filter((section) => SECTION_DEFINITIONS.some((item) => item.section_type === section.section_type))
    .sort((a, b) => Number(a.position || 0) - Number(b.position || 0));

  SECTION_DEFINITIONS.forEach((definition) => {
    if (!byType.has(definition.section_type)) {
      ordered.push(defaultDocumentSections(documentPages).find(
        (section) => section.section_type === definition.section_type,
      ));
    }
  });

  const summary = ordered.find((section) => section.section_type === 'SUMMARY');
  const acceptance = ordered.find((section) => section.section_type === 'ACCEPTANCE');
  const middle = ordered.filter((section) => !['SUMMARY', 'ACCEPTANCE'].includes(section.section_type));
  const normalized = [summary, ...middle, acceptance].filter(Boolean).map((section, position) => {
    const definition = SECTION_DEFINITIONS.find((item) => item.section_type === section.section_type);
    return {
      section_type: section.section_type,
      enabled: definition?.required ? true : Boolean(section.enabled),
      position,
      title_th: section.title_th || definition?.title_th || '',
      title_en: section.title_en || definition?.title_en || '',
    };
  });
  return normalized;
}

export function toggleDocumentSection(sections, sectionType, enabled) {
  if (['SUMMARY', 'DETAILED_BOQ'].includes(sectionType)) return normalizeDocumentSections(sections);
  return normalizeDocumentSections(sections.map((section) => (
    section.section_type === sectionType ? { ...section, enabled } : section
  )));
}

export function moveDocumentSection(sections, sectionType, direction) {
  const ordered = normalizeDocumentSections(sections);
  if (['SUMMARY', 'ACCEPTANCE'].includes(sectionType)) return ordered;
  const index = ordered.findIndex((section) => section.section_type === sectionType);
  const target = direction === 'up' ? index - 1 : index + 1;
  if (index < 0 || target < 1 || target >= ordered.length - 1) return ordered;
  [ordered[index], ordered[target]] = [ordered[target], ordered[index]];
  return ordered.map((section, position) => ({ ...section, position }));
}

export function normalizeVisualPages(pages = []) {
  return [...(pages || [])]
    .sort((a, b) => Number(a.position || 0) - Number(b.position || 0))
    .map((page, position) => ({
      position,
      layout: ['SINGLE', 'TWO_UP', 'FOUR_UP'].includes(page.layout) ? page.layout : 'TWO_UP',
      title_th: page.title_th || '',
      title_en: page.title_en || '',
      description_th: page.description_th || '',
      description_en: page.description_en || '',
      entries: [...(page.entries || [])]
        .sort((a, b) => Number(a.position || 0) - Number(b.position || 0))
        .map((entry, entryPosition) => ({
          media_id: entry.media_id,
          position: entryPosition,
          scope_logical_id: entry.scope_logical_id || null,
          caption_th: entry.caption_th || '',
          caption_en: entry.caption_en || '',
        })),
    }));
}

export function createVisualPage(mediaId = null, position = 0) {
  return {
    position,
    layout: 'TWO_UP',
    title_th: 'รูปภาพและรายละเอียดงาน',
    title_en: 'Visual / Work Detail',
    description_th: '',
    description_en: '',
    entries: mediaId ? [{
      media_id: mediaId,
      position: 0,
      scope_logical_id: null,
      caption_th: '',
      caption_en: '',
    }] : [],
  };
}

export function addMediaToVisualPages(pages, mediaId) {
  const normalized = normalizeVisualPages(pages);
  const alreadyUsed = normalized.some((page) => page.entries.some((entry) => entry.media_id === mediaId));
  if (alreadyUsed) return normalized;
  const last = normalized.at(-1);
  const capacity = { SINGLE: 1, TWO_UP: 2, FOUR_UP: 4 }[last?.layout] || 0;
  if (!last || last.entries.length >= capacity) {
    return normalizeVisualPages([...normalized, createVisualPage(mediaId, normalized.length)]);
  }
  return normalized.map((page, index) => (
    index === normalized.length - 1
      ? {
          ...page,
          entries: [...page.entries, {
            media_id: mediaId,
            position: page.entries.length,
            scope_logical_id: null,
            caption_th: '',
            caption_en: '',
          }],
        }
      : page
  ));
}

export function updateVisualPage(pages, pageIndex, updates) {
  return normalizeVisualPages(pages.map((page, index) => (
    index === pageIndex ? { ...page, ...updates } : page
  )));
}

export function removeVisualPage(pages, pageIndex) {
  return normalizeVisualPages(pages.filter((_, index) => index !== pageIndex));
}

export function moveVisualPage(pages, pageIndex, direction) {
  const ordered = normalizeVisualPages(pages);
  const target = direction === 'up' ? pageIndex - 1 : pageIndex + 1;
  if (target < 0 || target >= ordered.length) return ordered;
  [ordered[pageIndex], ordered[target]] = [ordered[target], ordered[pageIndex]];
  return normalizeVisualPages(ordered);
}

export function removeVisualEntry(pages, pageIndex, mediaId) {
  const remaining = pages[pageIndex].entries.filter((entry) => entry.media_id !== mediaId);
  if (!remaining.length) return removeVisualPage(pages, pageIndex);
  return updateVisualPage(pages, pageIndex, { entries: remaining });
}

export function updateVisualEntry(pages, pageIndex, mediaId, updates) {
  return updateVisualPage(pages, pageIndex, {
    entries: pages[pageIndex].entries.map((entry) => (
      entry.media_id === mediaId ? { ...entry, ...updates } : entry
    )),
  });
}

export function legacyPagesFromSections(sections) {
  const enabled = new Set(normalizeDocumentSections(sections)
    .filter((section) => section.enabled)
    .map((section) => section.section_type));
  return [
    'BOQ',
    ...(enabled.has('PAYMENT_TERMS') ? ['PAYMENT_TERMS'] : []),
    ...(enabled.has('TERMS') ? ['COMMERCIAL_TERMS'] : []),
  ];
}

export function enabledSections(document) {
  const compositionSections = document?.composition?.sections;
  const quotationSections = document?.quotation?.document_sections;
  return normalizeDocumentSections(
    compositionSections || quotationSections,
    document?.quotation?.document_pages,
  ).filter((section) => section.enabled);
}

export function chunkScopeRows(rows, size = 12) {
  const included = (rows || []).filter((row) => row.inclusion_state !== 'EXCLUDED');
  if (!included.length) return [[]];
  const chunks = [];
  let current = [];
  included.forEach((row) => {
    if (current.length >= size && row.node_kind === 'ITEM') {
      chunks.push(current);
      current = [];
    }
    current.push(row);
  });
  if (current.length) chunks.push(current);
  return chunks;
}

export function draftDocumentFromRevision(revision, quotation) {
  return {
    schema_version: DOCUMENT_SCHEMA_VERSION,
    project: { id: revision.project_id, name: revision.project_name },
    document: {
      id: revision.document_id,
      number: revision.document_number,
      kind: revision.document_kind,
      direction: revision.direction,
    },
    revision: {
      id: revision.revision_id,
      number: revision.revision_number,
      status: revision.status,
      source_version: revision.version,
    },
    calculation: {
      version: revision.calculation_version,
      subtotal: quotation.subtotal,
      discount_amount: quotation.discount_amount,
      net_sell_ex_vat: quotation.net_sell_ex_vat,
      vat_rate: quotation.vat_rate,
      vat_amount: quotation.vat_amount,
      grand_total: quotation.grand_total,
    },
    quotation,
    composition: {
      schema_version: DOCUMENT_SCHEMA_VERSION,
      sections: quotation.document_sections,
      visual_pages: quotation.visual_pages,
      media_assets: quotation.media_assets,
    },
    scope: revision.nodes || [],
  };
}
