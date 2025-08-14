"use client";

import { useState } from "react";
import { useAuth, useSignIn } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useClerk } from "@clerk/nextjs";
export default function ResetPasswordPage() {
  const [email, setEmail] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const { isSignedIn } = useAuth();
  const { signIn } = useSignIn();
  const router = useRouter();
  const { signOut } = useClerk();
  // Removed automatic redirect for signed-in users
  // Users may want to reset their password even when logged in

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setMessage(null);

    try {
// Sign out first if user is signed in
      if (isSignedIn) {
          await signOut();
        }
      // Create a password reset flow
      await signIn?.create({
        strategy: "reset_password_email_code",
        identifier: email,
      });

      setMessage({
        type: "success",
        text: "Password reset email sent! Check your inbox for instructions.",
      });
      setEmail("");
    } catch (error: any) {
      console.error("Password reset error:", error);
      setMessage({
        type: "error",
        text: error.errors?.[0]?.message || "Failed to send reset email. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleMagicLink = async () => {
    if (!email) {
      setMessage({ type: "error", text: "Please enter your email address first." });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      // Create a magic link sign-in
      await signIn?.create({
        strategy: "email_link",
        identifier: email,
        redirectUrl: `${window.location.origin}/auth-callback`,
      });

      setMessage({
        type: "success",
        text: "Magic link sent! Check your email to sign in.",
      });
    } catch (error: any) {
      console.error("Magic link error:", error);
      setMessage({
        type: "error",
        text: error.errors?.[0]?.message || "Failed to send magic link. Please try again.",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-green-100">
      <div className="w-full max-w-md p-8">
        <div className="bg-white shadow-xl rounded-2xl p-8 border border-gray-100">
          <div className="text-center mb-6">
            <h1 className="text-2xl font-bold text-gray-900 mb-2">Reset Your Password</h1>
            <p className="text-gray-600">Enter your email to receive reset instructions</p>
          </div>

          {isSignedIn && (
            <div className="mb-4 p-3 rounded-lg bg-blue-50 text-blue-800 border border-blue-200">
              <p className="text-sm">
                You're currently signed in. You can also{" "}
                <a href="/user-profile" className="font-semibold underline">
                  manage your password in your profile
                </a>
                .
              </p>
            </div>
          )}

          {message && (
            <div
              className={`mb-4 p-3 rounded-lg ${
                message.type === "success"
                  ? "bg-green-50 text-green-800 border border-green-200"
                  : "bg-red-50 text-red-800 border border-red-200"
              }`}
            >
              {message.text}
            </div>
          )}

          <form onSubmit={handleResetPassword} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-gray-700 font-medium mb-2">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 focus:bg-white focus:border-green-500 transition-all duration-200"
                placeholder="your@email.com"
                required
                disabled={isLoading}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-3 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? "Sending..." : "Send Reset Email"}
            </button>
          </form>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-white text-gray-500">Or</span>
            </div>
          </div>

          <button
            onClick={handleMagicLink}
            disabled={isLoading || !email}
            className="w-full bg-white border-2 border-gray-200 hover:bg-gray-50 text-gray-700 font-medium py-3 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i className="bi bi-envelope me-2"></i>
            Sign in with Magic Link
          </button>

          <div className="mt-6 text-center">
            <a
              href="/sign-in"
              className="text-green-600 hover:text-green-700 font-medium transition-colors duration-200"
            >
              Back to Sign In
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
