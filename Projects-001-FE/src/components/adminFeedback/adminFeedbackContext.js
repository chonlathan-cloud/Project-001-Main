import { createContext, useContext } from 'react';

export const AdminFeedbackContext = createContext(null);

export function useAdminFeedback() {
  const value = useContext(AdminFeedbackContext);
  if (!value) {
    throw new Error('useAdminFeedback must be used inside AdminFeedbackProvider');
  }
  return value;
}
