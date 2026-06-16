const toNumber = (value, fallback = 0) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
};

export const sumLineItems = (items = []) =>
  items.reduce((total, item) => total + toNumber(item?.amount), 0);

export const createEmptyLineItem = (overrides = {}) => ({
  id: overrides.id || '',
  description: overrides.description || '',
  qty: overrides.qty ?? 1,
  unit_price: overrides.unit_price ?? overrides.price ?? 0,
  amount: overrides.amount ?? toNumber(overrides.qty ?? 1, 1) * toNumber(overrides.unit_price ?? overrides.price),
  work_type: overrides.work_type || '',
  request_type: overrides.request_type || '',
});
