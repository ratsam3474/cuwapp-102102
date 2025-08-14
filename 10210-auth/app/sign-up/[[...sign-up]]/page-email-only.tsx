"use client";

import { SignUp, useUser } from "@clerk/nextjs";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SignUpPage() {
  const { user, isLoaded } = useUser();
  const router = useRouter();

  useEffect(() => {
    // If user is already signed in, redirect to auth-callback
    if (isLoaded && user) {
      router.push('/auth-callback');
    }
  }, [isLoaded, user, router]);
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-green-100">
      <div className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Create Your Account</h1>
          <p className="text-gray-600">Join Cuwhapp today - Email only, no phone required</p>
        </div>
        
        <SignUp
          fallbackRedirectUrl="/auth-callback"
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "bg-white shadow-xl rounded-2xl p-8 border border-gray-100",
              headerTitle: "hidden",
              headerSubtitle: "hidden",
              socialButtonsBlockButton: 
                "bg-white border-2 border-gray-200 hover:bg-gray-50 text-gray-700 font-medium transition-all duration-200",
              socialButtonsBlockButtonText: "font-medium",
              dividerRow: "my-6",
              dividerText: "text-gray-400",
              formFieldLabel: "text-gray-700 font-medium mb-2",
              formFieldInput: 
                "bg-gray-50 border-gray-200 rounded-lg px-4 py-3 focus:bg-white focus:border-green-500 transition-all duration-200",
              formButtonPrimary: 
                "bg-green-600 hover:bg-green-700 text-white font-medium py-3 rounded-lg transition-all duration-200",
              footerActionLink: 
                "text-green-600 hover:text-green-700 font-medium transition-colors duration-200",
              identityPreviewText: "text-gray-700",
              identityPreviewEditButton: "text-green-600 hover:text-green-700",
              formFieldInputShowPasswordButton: "text-gray-500 hover:text-gray-700",
              otpCodeFieldInput: "border-gray-300 focus:border-green-500",
              formResendCodeLink: "text-green-600 hover:text-green-700",
            },
            layout: {
              socialButtonsPlacement: "top",
              socialButtonsVariant: "blockButton",
              showOptionalFields: false,
            },
            variables: {
              colorPrimary: "#16a34a",
            }
          }}
        />
      </div>
    </div>
  );
}