"use client";
import { useEffect, useState } from 'react';
import { User, LogOut } from 'lucide-react';

interface CachedUser {
  id: string;
  email: string;
  username: string;
  isLoggedIn: boolean;
}

export const UserStatus = () => {
  const [user, setUser] = useState<CachedUser | null>(null);

  useEffect(() => {
    // Check for cached user
    const checkUser = () => {
      const cached = localStorage.getItem('cuwhapp_user_cache');
      if (cached) {
        try {
          const userData = JSON.parse(cached);
          if (userData.isLoggedIn) {
            setUser(userData);
          }
        } catch (e) {
          console.error('Error parsing user cache:', e);
        }
      }
    };

    checkUser();
    
    // Check periodically for changes
    const interval = setInterval(checkUser, 5000);
    
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    if (confirm('Are you sure you want to logout?')) {
      // Clear all caches
      localStorage.removeItem('cuwhapp_user_cache');
      localStorage.removeItem('whatsapp_agent_user');
      localStorage.removeItem('userCache');
      localStorage.removeItem('user_subscription');
      
      // Redirect to Clerk logout page with return URL to landing page
      const authUrl = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'https://auth.cuwapp.com';
      const landingUrl = process.env.NEXT_PUBLIC_LANDING_PAGE_URL || 'https://cuwapp.com';
      window.location.href = `${authUrl}/logout?redirect_url=` + encodeURIComponent(landingUrl);
    }
  };

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <a
          href={`${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'https://auth.cuwapp.com'}/sign-in`}
          className="px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-accent transition-colors"
        >
          Sign In
        </a>
        <a
          href={`${process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'https://auth.cuwapp.com'}/sign-up`}
          className="px-4 py-2 bg-white text-black border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          Sign Up
        </a>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-green-100 rounded-lg">
        <User className="w-4 h-4 text-green-600" />
        <div className="text-sm">
          <span className="font-medium text-gray-900">{user.username}</span>
          <span className="text-gray-500 ml-2 text-xs">{user.email}</span>
        </div>
      </div>
      <button
        onClick={handleLogout}
        className="px-3 py-1.5 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors text-sm flex items-center gap-1"
        title="Logout"
      >
        <LogOut className="w-4 h-4" />
        <span>Logout</span>
      </button>
    </div>
  );
};