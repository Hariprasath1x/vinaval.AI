import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { authService } from '../services/authService';
import Sidebar from '../components/Sidebar';
import { User, Mail, Shield, Save, Key, X } from 'lucide-react';
import './Profile.css';

export default function Profile() {
  const { user, updateProfile } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  // Change Password state
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [pwLoading, setPwLoading] = useState(false);
  const [pwSuccess, setPwSuccess] = useState('');
  const [pwError, setPwError] = useState('');

  const handleUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setSuccess('');
    setError('');

    try {
      if (updateProfile) {
        await updateProfile(name);
        setSuccess('Profile updated successfully!');
      } else {
        setSuccess('Profile details saved (local session only)');
      }
    } catch (err) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPwError('');
    setPwSuccess('');

    if (newPassword.length < 6) {
      setPwError('New password must be at least 6 characters.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setPwError('New passwords do not match.');
      return;
    }

    setPwLoading(true);
    try {
      await authService.changePassword(currentPassword, newPassword);
      setPwSuccess('Password updated successfully!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => {
        setShowPasswordModal(false);
        setPwSuccess('');
      }, 1500);
    } catch (err) {
      setPwError(err.message || 'Failed to change password');
    } finally {
      setPwLoading(false);
    }
  };

  return (
    <div className="profile-container">
      <Sidebar />
      <main className="profile-main animate-fade-in">
        <header className="profile-header">
          <h1>My Profile</h1>
          <p>Manage your account settings and preferences.</p>
        </header>

        <div className="profile-content">
          <div className="profile-card">
            <h2><User size={24} /> Personal Information</h2>
            
            {success && <div className="success-msg">{success}</div>}
            {error && <div className="error-msg">{error}</div>}

            <form onSubmit={handleUpdate}>
              <div className="form-group">
                <label>Full Name</label>
                <div style={{ position: 'relative' }}>
                  <User size={18} style={{ position: 'absolute', left: '1rem', top: '1rem', color: 'var(--text-secondary)' }} />
                  <input 
                    type="text" 
                    value={name} 
                    onChange={(e) => setName(e.target.value)}
                    style={{ paddingLeft: '2.5rem' }}
                    required
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Email Address</label>
                <div style={{ position: 'relative' }}>
                  <Mail size={18} style={{ position: 'absolute', left: '1rem', top: '1rem', color: 'var(--text-secondary)' }} />
                  <input 
                    type="email" 
                    value={user?.email || ''} 
                    disabled
                    style={{ paddingLeft: '2.5rem' }}
                  />
                </div>
                <small style={{ color: 'var(--text-secondary)', marginTop: '0.5rem', display: 'block' }}>
                  Email address cannot be changed.
                </small>
              </div>

              <button type="submit" className="btn-update" disabled={loading || name === user?.name}>
                <Save size={18} />
                {loading ? 'Saving...' : 'Save Changes'}
              </button>
            </form>
          </div>

          <div className="profile-card">
            <h2><Shield size={24} /> Security</h2>
            {user?.google_id ? (
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                You signed in with Google. Your password is managed by Google and cannot be updated here.
              </p>
            ) : (
              <>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                  Keep your account secure by using a strong password.
                </p>
                <button className="btn-secondary" onClick={() => setShowPasswordModal(true)}>
                  <Key size={16} style={{ marginRight: '6px' }} /> Change Password
                </button>
              </>
            )}
          </div>
        </div>

        {/* Change Password Modal */}
        {showPasswordModal && (
          <div className="modal-overlay" onClick={() => setShowPasswordModal(false)}>
            <div className="password-modal animate-fade-in" onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <h3><Key size={20} /> Change Password</h3>
                <button className="btn-close" onClick={() => setShowPasswordModal(false)}>
                  <X size={18} />
                </button>
              </div>

              {pwSuccess && <div className="success-msg">{pwSuccess}</div>}
              {pwError && <div className="error-msg">{pwError}</div>}

              <form onSubmit={handleChangePassword}>
                <div className="form-group">
                  <label>Current Password</label>
                  <input 
                    type="password"
                    value={currentPassword}
                    onChange={e => setCurrentPassword(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>New Password (min 6 characters)</label>
                  <input 
                    type="password"
                    value={newPassword}
                    onChange={e => setNewPassword(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>Confirm New Password</label>
                  <input 
                    type="password"
                    value={confirmPassword}
                    onChange={e => setConfirmPassword(e.target.value)}
                    required
                  />
                </div>

                <div className="modal-actions">
                  <button type="button" className="btn-secondary" onClick={() => setShowPasswordModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary" disabled={pwLoading}>
                    {pwLoading ? 'Updating...' : 'Update Password'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
