"use client";

import { UserProfile } from "@clerk/nextjs";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Link from "next/link";
import { ClerkLogo } from "../../_template/components/clerk-logo";
import { NextLogo } from "../../_template/components/next-logo";

export default function UserProfilePage() {
  const { isSignedIn, isLoaded } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in');
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-green-100">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (!isSignedIn) {
    return null; // Will redirect via useEffect
  }

  return (
    <main className="max-w-4xl w-full mx-auto p-6">
      <header className="flex items-center justify-between w-full h-16 gap-4 mb-8">
        <div className="flex gap-4">
          <div className="bg-[#F4F4F5] px-4 py-3 rounded-full inline-flex gap-4">
            <ClerkLogo />
            <div aria-hidden className="w-px h-6 bg-[#C7C7C8]" />
            <NextLogo />
          </div>
        </div>
        <div className="flex items-center gap-4">
          <Link
            href={process.env.NEXT_PUBLIC_API_URL || 'http://174.138.55.42:8000'}
            className="flex items-center gap-2 font-medium text-[0.8125rem] rounded-full px-4 py-2 hover:bg-gray-100 border"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Back to Dashboard
          </Link>
        </div>
      </header>
      
      <div className="flex justify-center">
        <UserProfile 
          routing="path"
          path="/user-profile"
        />
      </div>
    </main>
  );
}