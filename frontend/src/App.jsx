import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Welcome from './pages/Welcome';
import Auth from './pages/Auth';
import Dashboard from './pages/Dashboard';
import SelectExam from './pages/SelectExam';
import Space from './pages/Space';
import Profile from './pages/Profile';
import MockTests from './pages/MockTests';

const ProtectedRoute = ({ children }) => {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function AppRoutes() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route 
        path="/" 
        element={user ? <Navigate to="/dashboard" replace /> : <Welcome />} 
      />
      <Route 
        path="/welcome" 
        element={<Welcome />} 
      />
      <Route 
        path="/login" 
        element={user ? <Navigate to="/dashboard" replace /> : <Auth />} 
      />
      <Route 
        path="/signup" 
        element={user ? <Navigate to="/dashboard" replace /> : <Auth />} 
      />
      <Route 
        path="/dashboard" 
        element={<ProtectedRoute><Dashboard /></ProtectedRoute>} 
      />
      <Route 
        path="/select-exam" 
        element={<ProtectedRoute><SelectExam /></ProtectedRoute>} 
      />
      <Route 
        path="/space/:spaceId" 
        element={<ProtectedRoute><Space /></ProtectedRoute>} 
      />
      <Route 
        path="/profile" 
        element={<ProtectedRoute><Profile /></ProtectedRoute>} 
      />
      <Route 
        path="/mock-tests" 
        element={<ProtectedRoute><MockTests /></ProtectedRoute>} 
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;
