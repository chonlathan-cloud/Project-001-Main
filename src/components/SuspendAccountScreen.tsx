import { useState } from 'react';
import { ArrowLeft, X } from 'lucide-react';

interface SuspendAccountScreenProps {
  memberId: string;
  memberName: string;
  onBack: () => void;
}

export default function SuspendAccountScreen({ memberId, memberName, onBack }: SuspendAccountScreenProps) {
  const [suspensionReason, setSuspensionReason] = useState('');
  const [additionalNotes, setAdditionalNotes] = useState('');
  const [isConfirming, setIsConfirming] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSuspend = () => {
    setIsConfirming(true);
  };

  const handleConfirmSuspend = () => {
    setIsSuccess(true);
    setTimeout(() => {
      onBack();
    }, 2000);
  };

  const handleCancel = () => {
    setIsConfirming(false);
  };

  if (isSuccess) {
    return (
      <div className="flex-1 overflow-y-auto bg-[#FAF8F6]">
        <div className="flex items-center justify-center h-full">
          <div className="bg-white rounded-2xl border border-zinc-200/60 shadow-lg p-12 max-w-md mx-auto text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-zinc-900 mb-2">Account Suspended</h2>
            <p className="text-zinc-600 mb-6">
              {memberName}'s account has been successfully suspended.
            </p>
            <p className="text-sm text-zinc-500">
              The user will be notified of this action.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (isConfirming) {
    return (
      <div className="flex-1 overflow-y-auto bg-[#FAF8F6]">
        <div className="flex items-center justify-center h-full">
          <div className="bg-white rounded-2xl border border-zinc-200/60 shadow-lg p-8 max-w-md mx-auto">
            <div className="flex items-start gap-4 mb-6">
              <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4v2m0 4v2M7.08 6.47a9 9 0 1 1 9.84 0" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-bold text-zinc-900">Confirm Suspension</h2>
                <p className="text-sm text-zinc-600 mt-1">This action cannot be undone immediately.</p>
              </div>
            </div>

            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
              <p className="text-sm text-red-800">
                <strong>Warning:</strong> Suspending {memberName}'s account will:
              </p>
              <ul className="text-sm text-red-700 mt-2 space-y-1 ml-4 list-disc">
                <li>Immediately revoke all access</li>
                <li>Disable all project assignments</li>
                <li>Prevent login and API access</li>
                <li>Lock all pending approvals</li>
              </ul>
            </div>

            <div className="mb-6">
              <p className="text-sm font-medium text-zinc-900 mb-2">Reason for suspension:</p>
              <p className="text-sm text-zinc-600 bg-zinc-50 rounded-lg p-3 border border-zinc-200">
                {suspensionReason || 'Not specified'}
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={handleCancel}
                className="flex-1 px-4 py-2.5 border border-zinc-300 text-zinc-900 font-medium rounded-lg hover:bg-zinc-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmSuspend}
                className="flex-1 px-4 py-2.5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors"
              >
                Confirm Suspension
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto bg-[#FAF8F6]">
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="bg-white border-b border-zinc-200/60 px-8 py-6 sticky top-0 z-10">
          <div className="max-w-4xl mx-auto">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-zinc-600 hover:text-zinc-900 transition-colors mb-4"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm font-medium">Settings {`>`} User Management {`>`} Member Details</span>
            </button>
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-zinc-900">Suspend Account</h1>
                <p className="text-sm text-zinc-600 mt-1">
                  Temporarily disable access for {memberName}
                </p>
              </div>
              <div className="flex items-center gap-2 px-3 py-1 bg-red-50 border border-red-200 rounded-full">
                <span className="inline-block w-2 h-2 bg-red-500 rounded-full"></span>
                <span className="text-xs font-semibold text-red-700">SUSPENSION</span>
              </div>
            </div>
          </div>
        </div>

        {/* Main content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-4xl mx-auto px-8 py-8">
            <div className="grid grid-cols-3 gap-8">
              {/* Left column - Account Information */}
              <div className="col-span-1">
                <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-6">
                  <h2 className="text-lg font-bold text-zinc-900 mb-6">Account Information</h2>

                  <div className="space-y-6">
                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Member ID</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{memberId}</p>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Full Name</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">{memberName}</p>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Current Status</label>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="inline-block w-2 h-2 bg-emerald-500 rounded-full"></span>
                        <span className="text-sm text-zinc-900 font-medium">ACTIVE</span>
                      </div>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Last Login</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">Today at 09:45 AM</p>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">Active Sessions</label>
                      <p className="text-sm text-zinc-900 font-medium mt-1">2 sessions</p>
                    </div>
                  </div>
                </div>

                {/* Impact Summary */}
                <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-6 mt-6">
                  <h3 className="text-lg font-bold text-zinc-900 mb-4">Impact Summary</h3>

                  <div className="space-y-4">
                    <div className="flex items-start gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <span className="text-lg">📋</span>
                      <div>
                        <p className="text-sm font-medium text-blue-900">Projects Affected</p>
                        <p className="text-xs text-blue-800 mt-0.5">5 active projects</p>
                      </div>
                    </div>

                    <div className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                      <span className="text-lg">⏳</span>
                      <div>
                        <p className="text-sm font-medium text-amber-900">Pending Approvals</p>
                        <p className="text-xs text-amber-800 mt-0.5">3 awaiting approval</p>
                      </div>
                    </div>

                    <div className="flex items-start gap-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
                      <span className="text-lg">🔗</span>
                      <div>
                        <p className="text-sm font-medium text-purple-900">API Access</p>
                        <p className="text-xs text-purple-800 mt-0.5">Will be revoked</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right column - Suspension Form */}
              <div className="col-span-2">
                <div className="bg-white rounded-xl border border-zinc-200/60 shadow-sm p-6">
                  <h2 className="text-lg font-bold text-zinc-900 mb-6">Suspension Details</h2>

                  <div className="space-y-6">
                    {/* Reason Selection */}
                    <div>
                      <label className="block text-sm font-semibold text-zinc-900 mb-3">Reason for Suspension</label>
                      <div className="space-y-2">
                        {[
                          { value: 'policy_violation', label: 'Policy Violation', description: 'User violated company policy' },
                          { value: 'security_breach', label: 'Security Breach', description: 'Account or credentials compromised' },
                          { value: 'performance', label: 'Performance Issues', description: 'Repeated performance concerns' },
                          { value: 'inactivity', label: 'Extended Inactivity', description: 'No activity for extended period' },
                          { value: 'other', label: 'Other', description: 'Please specify in notes below' }
                        ].map((reason) => (
                          <label key={reason.value} className="flex items-start gap-3 p-3 border border-zinc-200 rounded-lg hover:bg-zinc-50 cursor-pointer transition-colors">
                            <input
                              type="radio"
                              name="suspension_reason"
                              value={reason.value}
                              checked={suspensionReason === reason.value}
                              onChange={(e) => setSuspensionReason(e.target.value)}
                              className="mt-1"
                            />
                            <div className="flex-1">
                              <p className="text-sm font-medium text-zinc-900">{reason.label}</p>
                              <p className="text-xs text-zinc-600 mt-0.5">{reason.description}</p>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Additional Notes */}
                    <div>
                      <label className="block text-sm font-semibold text-zinc-900 mb-2">Additional Notes</label>
                      <textarea
                        value={additionalNotes}
                        onChange={(e) => setAdditionalNotes(e.target.value)}
                        placeholder="Provide any additional context or details about this suspension..."
                        className="w-full px-4 py-3 border border-zinc-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
                        rows={6}
                      />
                      <p className="text-xs text-zinc-600 mt-2">{additionalNotes.length}/500 characters</p>
                    </div>

                    {/* Notification Preference */}
                    <div>
                      <label className="block text-sm font-semibold text-zinc-900 mb-3">Notification</label>
                      <label className="flex items-center gap-3 p-3 border border-zinc-200 rounded-lg hover:bg-zinc-50 cursor-pointer transition-colors">
                        <input
                          type="checkbox"
                          defaultChecked
                          className="w-4 h-4 rounded border-zinc-300"
                        />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-zinc-900">Notify user via email</p>
                          <p className="text-xs text-zinc-600 mt-0.5">User will receive notification about account suspension</p>
                        </div>
                      </label>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3 pt-4 border-t border-zinc-200">
                      <button
                        onClick={onBack}
                        className="flex-1 px-4 py-2.5 border border-zinc-300 text-zinc-900 font-medium rounded-lg hover:bg-zinc-50 transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSuspend}
                        disabled={!suspensionReason}
                        className={`flex-1 px-4 py-2.5 font-medium rounded-lg transition-colors ${
                          suspensionReason
                            ? 'bg-red-600 text-white hover:bg-red-700'
                            : 'bg-zinc-200 text-zinc-500 cursor-not-allowed'
                        }`}
                      >
                        Suspend Account
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
