"use client";

import { useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';

function AuthSuccessContent() {
  const searchParams = useSearchParams();

  useEffect(() => {
    // Get user data from URL params
    const userId = searchParams.get('userId');
    const email = searchParams.get('email');
    const username = searchParams.get('username');
    const firstName = searchParams.get('firstName');
    const lastName = searchParams.get('lastName');
    const token = searchParams.get('token');
    const redirect = searchParams.get('redirect');

    if (userId && email) {
      // Create user cache object
      const userData = {
        id: userId,
        email: email,
        username: username || email.split('@')[0],
        firstName: firstName || '',
        lastName: lastName || '',
        fullName: `${firstName || ''} ${lastName || ''}`.trim(),
        token: token || '',
        isLoggedIn: true,
        lastUpdated: new Date().toISOString()
      };

      // Save to all cache keys for cross-domain compatibility
      localStorage.setItem('cuwhapp_user_cache', JSON.stringify(userData));
      localStorage.setItem('whatsapp_agent_user', JSON.stringify(userData));
      localStorage.setItem('userCache', JSON.stringify(userData));

      // Redirect based on the redirect param
      if (redirect === 'dashboard') {
        // Pass the same params to dashboard for it to set its own cache
        const dashboardParams = new URLSearchParams({
          userId: userId,
          email: email,
          username: username || '',
          token: token || '',
          isNewLogin: 'true'
        });
        const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'https://app.cuwapp.com';
        window.location.href = `${apiUrl}?${dashboardParams.toString()}`;
      } else {
        // Default to landing page home
        const landingUrl = process.env.NEXT_PUBLIC_LANDING_PAGE_URL || 'https://cuwapp.com';
        window.location.href = landingUrl;
      }
    } else {
      // No user data, redirect to sign-in
      const authUrl = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'https://auth.cuwapp.com';
      window.location.href = `${authUrl}/sign-in`;
    }
  }, [searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-black">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
        <p className="mt-4 text-white">Setting up your account...</p>
      </div>
    </div>
  );
}

export default function AuthSuccess() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-white">Loading...</p>
        </div>
      </div>
    }>
      <AuthSuccessContent />
    </Suspense>
  );
}