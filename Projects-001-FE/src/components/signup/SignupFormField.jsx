import React from 'react';

const SignupFormField = ({
  children,
  className = '',
  icon: Icon,
  id,
  label,
}) => (
  <div className={`signup-field ${className}`.trim()}>
    <label className="signup-field-label" htmlFor={id}>
      {label}
    </label>
    <div className="signup-field-control">
      {Icon ? <Icon aria-hidden="true" size={18} /> : null}
      {children}
    </div>
  </div>
);

export default SignupFormField;
