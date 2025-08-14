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
        await signOut({ redirectUrl: 'https://cuwapp.com' });
      } catch (error) {
        console.error('Logout error:', error);
        // Fallback redirect
        window.location.href = 'https://cuwapp.com';
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