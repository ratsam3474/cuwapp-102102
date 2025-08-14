"use client";

import { useEffect, useState } from 'react';
import { useUser, useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';

export default function SyncSession() {
  const { user, isLoaded } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState('Syncing session...');

  useEffect(() => {
    const syncSession = async () => {
      if (!isLoaded) return;
      
      if (user) {
        setStatus('Found active Clerk session, updating cache...');
        
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
        localStorage.setItem('cuwhapp_user_cache', JSON.stringify(userData));
        localStorage.setItem('whatsapp_agent_user', JSON.stringify(userData));
        
        // Sync with backend
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://app.cuwapp.com';
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
            setStatus('Session synced successfully! Redirecting...');
          }
        } catch (error) {
          console.error('Failed to sync with backend:', error);
          setStatus('Session cached locally. Redirecting...');
        }
        
        // Redirect to dashboard
        setTimeout(() => {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://app.cuwapp.com';
          window.location.href = apiUrl;
        }, 1500);
        
      } else {
        setStatus('No active session found. Redirecting to sign-in...');
        setTimeout(() => {
          router.push('/sign-in');
        }, 1500);
      }
    };
    
    syncSession();
  }, [isLoaded, user, getToken, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-green-100">
      <div className="text-center p-8 bg-white rounded-lg shadow-lg">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto mb-4"></div>
        <h2 className="text-lg font-semibold text-gray-800 mb-2">Session Sync</h2>
        <p className="text-gray-600">{status}</p>
      </div>
    </div>
  );
}
