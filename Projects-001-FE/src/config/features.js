const enabledValues = new Set(['1', 'true', 'yes', 'on']);

export const BOQ_V2_ENABLED = enabledValues.has(
  String(import.meta.env.VITE_BOQ_V2_ENABLED || '').trim().toLowerCase()
);

