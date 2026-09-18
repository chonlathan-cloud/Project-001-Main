const COMPONENT_TYPES = ['MATERIAL', 'LABOR'];

function createUuid() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function componentTemplate(componentType) {
  return {
    id: null,
    component_type: componentType,
    quantity_basis: 'INHERITED',
    quantity: null,
    unit: null,
    specification: null,
    cost_state: 'UNKNOWN',
    unit_rate: null,
    explicit_zero_reason: null,
  };
}

export function createDraftNode(nodeKind, parentLogicalId = null, position = 0) {
  const item = nodeKind === 'ITEM';
  return {
    id: null,
    logical_id: createUuid(),
    parent_logical_id: parentLogicalId,
    node_kind: nodeKind,
    inclusion_state: 'REQUIRED',
    position,
    item_code: null,
    catalog_item_id: null,
    catalog_item_version: null,
    source_logical_id: null,
    description: '',
    specification: null,
    quantity: item ? '1.0000' : null,
    unit: item ? 'งาน' : null,
    sell_material_unit_rate: item ? '0.0000' : null,
    sell_labor_unit_rate: item ? '0.0000' : null,
    sell_total: '0.00',
    components: item ? COMPONENT_TYPES.map(componentTemplate) : [],
  };
}

function descendantsOf(nodes, logicalId) {
  const descendants = new Set([logicalId]);
  let changed = true;
  while (changed) {
    changed = false;
    nodes.forEach((node) => {
      if (node.parent_logical_id && descendants.has(node.parent_logical_id) && !descendants.has(node.logical_id)) {
        descendants.add(node.logical_id);
        changed = true;
      }
    });
  }
  return descendants;
}

function orderedTree(nodes) {
  const children = new Map();
  nodes.forEach((node) => {
    const key = node.parent_logical_id || '';
    const siblings = children.get(key) || [];
    siblings.push(node);
    children.set(key, siblings);
  });
  children.forEach((siblings) => siblings.sort((a, b) => a.position - b.position));

  const result = [];
  const visited = new Set();
  const visit = (parentId, depth = 0) => {
    (children.get(parentId || '') || []).forEach((node) => {
      if (visited.has(node.logical_id)) return;
      visited.add(node.logical_id);
      result.push({ ...node, depth });
      visit(node.logical_id, depth + 1);
    });
  };
  visit(null);
  nodes.forEach((node) => {
    if (!visited.has(node.logical_id)) result.push({ ...node, depth: 0 });
  });
  return result;
}

export function normalizeSiblingPositions(nodes) {
  const nextPositions = new Map();
  const next = orderedTree(nodes).map((node) => {
    const parentKey = node.parent_logical_id || '';
    const position = nextPositions.get(parentKey) || 0;
    nextPositions.set(parentKey, position + 1);
    return { ...node, position };
  });
  return orderedTree(next);
}

export function addDraftNode(nodes, nodeKind, parentLogicalId = null) {
  const siblingCount = nodes.filter(
    (node) => (node.parent_logical_id || null) === (parentLogicalId || null)
  ).length;
  return normalizeSiblingPositions([
    ...nodes,
    createDraftNode(nodeKind, parentLogicalId, siblingCount),
  ]);
}

export function updateDraftNode(nodes, logicalId, updates) {
  return nodes.map((node) => (
    node.logical_id === logicalId ? { ...node, ...updates } : node
  ));
}

export function updateDraftComponent(nodes, logicalId, componentType, updates) {
  return nodes.map((node) => {
    if (node.logical_id !== logicalId) return node;
    const current = COMPONENT_TYPES.map((type) => (
      node.components?.find((component) => component.component_type === type)
      || componentTemplate(type)
    ));
    return {
      ...node,
      components: current.map((component) => (
        component.component_type === componentType
          ? { ...component, ...updates }
          : component
      )),
    };
  });
}

export function removeDraftNode(nodes, logicalId) {
  const removed = descendantsOf(nodes, logicalId);
  return normalizeSiblingPositions(
    nodes.filter((node) => !removed.has(node.logical_id))
  );
}

export function duplicateDraftItem(nodes, logicalId) {
  const source = nodes.find((node) => node.logical_id === logicalId);
  if (!source || source.node_kind !== 'ITEM') return nodes;
  const duplicate = {
    ...source,
    id: null,
    logical_id: createUuid(),
    source_logical_id: source.source_logical_id || source.logical_id,
    description: source.description ? `${source.description} (สำเนา)` : 'รายการสำเนา',
    position: source.position + 1,
    components: (source.components || []).map((component) => ({
      ...component,
      id: null,
    })),
  };
  const shifted = nodes.map((node) => (
    (node.parent_logical_id || null) === (source.parent_logical_id || null)
      && node.position > source.position
      ? { ...node, position: node.position + 1 }
      : node
  ));
  return normalizeSiblingPositions([...shifted, duplicate]);
}

export function moveDraftNode(nodes, logicalId, direction) {
  const source = nodes.find((node) => node.logical_id === logicalId);
  if (!source) return nodes;
  const siblings = nodes
    .filter((node) => (node.parent_logical_id || null) === (source.parent_logical_id || null))
    .sort((a, b) => a.position - b.position);
  const currentIndex = siblings.findIndex((node) => node.logical_id === logicalId);
  const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
  if (currentIndex < 0 || targetIndex < 0 || targetIndex >= siblings.length) return nodes;
  const target = siblings[targetIndex];
  return normalizeSiblingPositions(nodes.map((node) => {
    if (node.logical_id === source.logical_id) return { ...node, position: target.position };
    if (node.logical_id === target.logical_id) return { ...node, position: source.position };
    return node;
  }));
}

export function moveDraftNodeTo(nodes, logicalId, parentLogicalId) {
  const source = nodes.find((node) => node.logical_id === logicalId);
  const parent = parentLogicalId
    ? nodes.find((node) => node.logical_id === parentLogicalId)
    : null;
  if (!source || parent?.node_kind === 'ITEM') return nodes;
  if (descendantsOf(nodes, logicalId).has(parentLogicalId)) return nodes;
  const position = nodes.filter(
    (node) => (node.parent_logical_id || null) === (parentLogicalId || null)
  ).length;
  return normalizeSiblingPositions(nodes.map((node) => (
    node.logical_id === logicalId
      ? { ...node, parent_logical_id: parentLogicalId || null, position }
      : node
  )));
}

function nullableDecimal(value) {
  const text = String(value ?? '').trim();
  return text === '' ? null : text;
}

export function normalizeQuotationDraft(quotation = {}) {
  return {
    title: quotation.title || '',
    customer_name: quotation.customer_name || '',
    customer_address: quotation.customer_address || '',
    customer_tax_id: quotation.customer_tax_id || '',
    customer_contact: quotation.customer_contact || '',
    quotation_date: quotation.quotation_date || '',
    valid_until: quotation.valid_until || '',
    currency: 'THB',
    vat_rate: quotation.vat_rate ?? '7.0000',
    discount_type: quotation.discount_type || 'NONE',
    discount_value: quotation.discount_value ?? '0.0000',
    subtotal: quotation.subtotal ?? '0.00',
    discount_amount: quotation.discount_amount ?? '0.00',
    net_sell_ex_vat: quotation.net_sell_ex_vat ?? '0.00',
    vat_amount: quotation.vat_amount ?? '0.00',
    grand_total: quotation.grand_total ?? '0.00',
    payment_schedule: (quotation.payment_schedule || []).map((item) => ({
      label: item.label || '',
      percentage: item.percentage ?? null,
      fixed_amount: item.fixed_amount ?? null,
    })),
    commercial_terms: [...(quotation.commercial_terms || [])],
    document_pages: quotation.document_pages?.length
      ? [...quotation.document_pages]
      : ['BOQ', 'PAYMENT_TERMS', 'COMMERCIAL_TERMS'],
  };
}

export function buildSavePayload(version, nodes, quotation) {
  const payload = {
    expected_version: version,
    nodes: normalizeSiblingPositions(nodes).map((node) => ({
      id: node.id || null,
      logical_id: node.logical_id,
      parent_logical_id: node.parent_logical_id || null,
      node_kind: node.node_kind,
      inclusion_state: node.inclusion_state || 'REQUIRED',
      position: node.position,
      item_code: node.item_code || null,
      catalog_item_id: node.catalog_item_id || null,
      catalog_item_version: node.catalog_item_version || null,
      source_logical_id: node.source_logical_id || null,
      description: node.description || null,
      specification: node.specification || null,
      quantity: node.node_kind === 'ITEM' ? nullableDecimal(node.quantity) : null,
      unit: node.node_kind === 'ITEM' ? node.unit || null : null,
      sell_material_unit_rate: node.node_kind === 'ITEM'
        ? nullableDecimal(node.sell_material_unit_rate)
        : null,
      sell_labor_unit_rate: node.node_kind === 'ITEM'
        ? nullableDecimal(node.sell_labor_unit_rate)
        : null,
      components: node.node_kind === 'ITEM'
        ? COMPONENT_TYPES.map((type) => {
            const component = node.components?.find((item) => item.component_type === type)
              || componentTemplate(type);
            return {
              id: component.id || null,
              component_type: type,
              quantity_basis: component.quantity_basis || 'INHERITED',
              quantity: component.quantity_basis === 'OVERRIDDEN'
                ? nullableDecimal(component.quantity)
                : null,
              unit: component.unit || null,
              specification: component.specification || null,
              cost_state: component.cost_state || 'UNKNOWN',
              unit_rate: component.cost_state === 'PRICED'
                ? nullableDecimal(component.unit_rate)
                : null,
              explicit_zero_reason: component.explicit_zero_reason || null,
            };
          })
        : [],
      confirm_financial_discard: Boolean(node.confirm_financial_discard),
    })),
  };
  if (quotation) {
    const {
      subtotal: _subtotal,
      discount_amount: _discountAmount,
      net_sell_ex_vat: _netSellExVat,
      vat_amount: _vatAmount,
      grand_total: _grandTotal,
      ...draft
    } = normalizeQuotationDraft(quotation);
    payload.quotation = draft;
  }
  return payload;
}

export function parseRevisionDraft(revision) {
  return normalizeSiblingPositions(
    (revision?.nodes || []).map((node) => ({
      ...node,
      description: node.description || '',
      components: (node.components || []).map((component) => ({ ...component })),
    }))
  );
}
