"use client";

import { useEffect } from 'react';
import { useClerk } from '@clerk/nextjs';
import { useRouter } from 'next/navigation';

export default function LogoutPage() {
  const { signOut } = useClerk();
  const router = useRouter();

  useEffect(() => {
    const handleLogout = async () => {
      try {
        // Clear all local storage caches
        if (typeof window !== 'undefined') {
          localStorage.removeItem('cuwhapp_user_cache');
          localStorage.removeItem('whatsapp_agent_user');
          localStorage.removeItem('user_subscription');
          
          // Clear all Cuwhapp related items
          const keysToRemove = [];
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && (key.includes('cuwhapp') || key.includes('whatsapp'))) {
              keysToRemove.push(key);
            }
          }
          keysToRemove.forEach(key => localStorage.removeItem(key));
        }
        
        // Sign out from Clerk and redirect
        const landingUrl = process.env.NEXT_PUBLIC_LANDING_PAGE_URL || 'https://cuwapp.com';
        await signOut({ redirectUrl: landingUrl });
      } catch (error) {
        console.error('Logout error:', error);
        // Fallback redirect
        const landingUrl = process.env.NEXT_PUBLIC_LANDING_PAGE_URL || 'https://cuwapp.com';
        window.location.href = landingUrl;
      }
    };

    handleLogout();
  }, [signOut]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-green-100">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Logging out...</p>
      </div>
    </div>
  );
}