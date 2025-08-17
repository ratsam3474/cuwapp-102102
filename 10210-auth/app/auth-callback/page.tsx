"use client";

import { useEffect } from 'react';
import { useUser, useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';

export default function AuthCallback() {
  const { user, isLoaded } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();

  useEffect(() => {
    const handleAuth = async () => {
      if (!isLoaded) return;
      
      if (user) {
        // Get the session token
        const token = await getToken();
        
        // Prepare user data for storage
        const userData = {
          id: user.id,
          email: user.primaryEmailAddress?.emailAddress || '',
          firstName: user.firstName || '',
          lastName: user.lastName || '',
          fullName: user.fullName || '',
          username: user.username || user.firstName || 'User',
          imageUrl: user.imageUrl || '',
          phone: user.primaryPhoneNumber?.phoneNumber || '',
          createdAt: user.createdAt,
          token: token,
          isLoggedIn: true,
          lastUpdated: new Date().toISOString()
        };
        
        // Store in unified cache
        const cacheData = {
          ...userData,
          isLoggedIn: true,
          lastUpdated: new Date().toISOString()
        };
        
        localStorage.setItem('cuwhapp_user_cache', JSON.stringify(cacheData));
        localStorage.setItem('whatsapp_agent_user', JSON.stringify(cacheData));
        
        // Create or update user subscription in backend
        try {
          // Use environment variable for API URL
          const apiUrl = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'https://app.cuwapp.com';
          const response = await fetch(`${apiUrl}/api/users/sync`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
              user_id: userData.id,
              email: userData.email,
              name: userData.fullName,
              metadata: {
                firstName: userData.firstName,
                lastName: userData.lastName,
                username: userData.username,
                phone: userData.phone
              }
            })
          });
          
          if (response.ok) {
            const subscriptionData = await response.json();
            localStorage.setItem('user_subscription', JSON.stringify(subscriptionData));
          }
        } catch (error) {
          console.error('Failed to sync user data:', error);
        }
        
        // Redirect directly to dashboard with user data
        const params = new URLSearchParams({
          userId: userData.id,
          email: userData.email,
          username: userData.username,
          token: userData.token || '',
          isNewLogin: 'true'
        });
        
        // Go directly to dashboard - it will set its own cache
        const dashboardUrl = process.env.NEXT_PUBLIC_API_GATEWAY_URL || 'https://app.cuwapp.com';
        window.location.href = `${dashboardUrl}?${params.toString()}`;
      } else {
        // No user, redirect to sign-in
        router.push('/sign-in');
      }
    };
    
    handleAuth();
  }, [isLoaded, user, getToken, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-green-100">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Authenticating...</p>
      </div>
    </div>
  );
}