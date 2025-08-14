import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import Link from "next/link";

export default function PrivacyPolicy() {
  return (
    <>
      <div className="overflow-x-hidden">
        <Navbar />
        
        {/* Hero Section */}
        <div className="bg-black text-white bg-[linear-gradient(to_bottom,#000,#0f3d0f_34%,#1a4d2e_65%,#2d5f3f_82%)] py-16 sm:py-24">
          <div className="container">
            <div className="max-w-4xl mx-auto text-center">
              <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-6">
                Privacy Policy
              </h1>
              <p className="text-xl text-gray-400">
                Your privacy is important to us. Learn how we protect your data.
              </p>
              <p className="text-sm text-gray-500 mt-4">
                Last updated: January 2025
              </p>
            </div>
          </div>
        </div>

        {/* Content Section */}
        <div className="bg-black text-white py-16">
          <div className="container">
            <div className="max-w-4xl mx-auto space-y-8">
              
              {/* Introduction */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-4 text-brand-primary">Introduction</h2>
                <p className="text-gray-300 leading-relaxed">
                  CuWhapp (&ldquo;we,&rdquo; &ldquo;our,&rdquo; or &ldquo;us&rdquo;) is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our WhatsApp automation and lead generation platform.
                </p>
              </div>

              {/* Information We Collect */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">Information We Collect</h2>
                
                <div className="space-y-6">
                  <div>
                    <h3 className="text-xl font-semibold mb-3 text-white">Account Information</h3>
                    <ul className="space-y-2 text-gray-300">
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Email address and username
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Phone number (for WhatsApp integration)
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Payment information (processed securely via Stripe)
                      </li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold mb-3 text-white">WhatsApp Data</h3>
                    <ul className="space-y-2 text-gray-300">
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        WhatsApp group member information (phone numbers, names)
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Message history for automation purposes
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Contact lists and lead information
                      </li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold mb-3 text-white">Usage Data</h3>
                    <ul className="space-y-2 text-gray-300">
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Campaign performance metrics
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Feature usage analytics
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Session and login information
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              {/* How We Use Your Information */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">How We Use Your Information</h2>
                
                <div className="space-y-4 text-gray-300">
                  <div className="flex items-start">
                    <div className="bg-green-500/20 p-2 rounded-lg mr-4">
                      <span className="text-green-500 text-xl">✓</span>
                    </div>
                    <div>
                      <h4 className="font-semibold text-white mb-1">Service Delivery</h4>
                      <p>To provide WhatsApp automation, lead generation, and campaign management services</p>
                    </div>
                  </div>

                  <div className="flex items-start">
                    <div className="bg-green-500/20 p-2 rounded-lg mr-4">
                      <span className="text-green-500 text-xl">✓</span>
                    </div>
                    <div>
                      <h4 className="font-semibold text-white mb-1">Communication</h4>
                      <p>To send service updates, security alerts, and support messages</p>
                    </div>
                  </div>

                  <div className="flex items-start">
                    <div className="bg-green-500/20 p-2 rounded-lg mr-4">
                      <span className="text-green-500 text-xl">✓</span>
                    </div>
                    <div>
                      <h4 className="font-semibold text-white mb-1">Improvement</h4>
                      <p>To analyze usage patterns and improve our platform features</p>
                    </div>
                  </div>

                  <div className="flex items-start">
                    <div className="bg-green-500/20 p-2 rounded-lg mr-4">
                      <span className="text-green-500 text-xl">✓</span>
                    </div>
                    <div>
                      <h4 className="font-semibold text-white mb-1">Compliance</h4>
                      <p>To comply with legal obligations and protect against fraud</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Data Security */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">Data Security</h2>
                <p className="text-gray-300 leading-relaxed mb-4">
                  We implement industry-standard security measures to protect your data:
                </p>
                <ul className="space-y-3 text-gray-300">
                  <li className="flex items-center">
                    <span className="text-green-500 mr-3">🔒</span>
                    End-to-end encryption for sensitive data
                  </li>
                  <li className="flex items-center">
                    <span className="text-green-500 mr-3">🛡️</span>
                    Secure SSL/TLS connections
                  </li>
                  <li className="flex items-center">
                    <span className="text-green-500 mr-3">🔐</span>
                    Regular security audits and updates
                  </li>
                  <li className="flex items-center">
                    <span className="text-green-500 mr-3">💾</span>
                    Encrypted data storage and backups
                  </li>
                </ul>
              </div>

              {/* Data Sharing */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">Data Sharing & Third Parties</h2>
                <p className="text-gray-300 leading-relaxed mb-4">
                  We do not sell your personal information. We may share data with:
                </p>
                <div className="space-y-4">
                  <div className="border-l-4 border-green-500 pl-4">
                    <h4 className="font-semibold text-white">Service Providers</h4>
                    <p className="text-gray-400 text-sm mt-1">
                      WhatsApp Business API, Stripe for payments, Clerk for authentication
                    </p>
                  </div>
                  <div className="border-l-4 border-green-500 pl-4">
                    <h4 className="font-semibold text-white">Legal Requirements</h4>
                    <p className="text-gray-400 text-sm mt-1">
                      When required by law or to protect rights and safety
                    </p>
                  </div>
                  <div className="border-l-4 border-green-500 pl-4">
                    <h4 className="font-semibold text-white">Business Transfers</h4>
                    <p className="text-gray-400 text-sm mt-1">
                      In case of merger, acquisition, or asset sale
                    </p>
                  </div>
                </div>
              </div>

              {/* Your Rights */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">Your Rights</h2>
                <p className="text-gray-300 leading-relaxed mb-6">
                  You have the right to:
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-black/50 p-4 rounded-lg border border-gray-700">
                    <h4 className="font-semibold text-white mb-2">Access Your Data</h4>
                    <p className="text-gray-400 text-sm">Request a copy of your personal information</p>
                  </div>
                  <div className="bg-black/50 p-4 rounded-lg border border-gray-700">
                    <h4 className="font-semibold text-white mb-2">Delete Your Data</h4>
                    <p className="text-gray-400 text-sm">Request deletion of your account and data</p>
                  </div>
                  <div className="bg-black/50 p-4 rounded-lg border border-gray-700">
                    <h4 className="font-semibold text-white mb-2">Export Your Data</h4>
                    <p className="text-gray-400 text-sm">Download your data in a portable format</p>
                  </div>
                  <div className="bg-black/50 p-4 rounded-lg border border-gray-700">
                    <h4 className="font-semibold text-white mb-2">Opt-Out</h4>
                    <p className="text-gray-400 text-sm">Unsubscribe from marketing communications</p>
                  </div>
                </div>
              </div>

              {/* Cookies */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">Cookies & Tracking</h2>
                <p className="text-gray-300 leading-relaxed">
                  We use cookies and similar technologies to enhance your experience, analyze usage, and remember your preferences. You can control cookie settings through your browser.
                </p>
              </div>

              {/* Contact */}
              <div className="bg-gradient-to-br from-brand-primary/20 to-brand-secondary/20 p-8 rounded-2xl border border-brand-primary/30">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">Contact Us</h2>
                <p className="text-gray-300 leading-relaxed mb-6">
                  If you have questions about this Privacy Policy or your data, please contact us:
                </p>
                <div className="space-y-3">
                  <p className="text-white">
                    <span className="text-gray-400">Email:</span> privacy@cuwapp.com
                  </p>
                  <p className="text-white">
                    <span className="text-gray-400">WhatsApp:</span> +1 (719) 493-8889
                  </p>
                </div>
              </div>

              {/* Updates */}
              <div className="text-center py-8 border-t border-gray-800">
                <p className="text-gray-400">
                  This policy may be updated periodically. We&apos;ll notify you of significant changes via email or platform notification.
                </p>
                <div className="mt-6">
                  <Link 
                    href="/"
                    className="inline-block bg-brand-primary hover:bg-brand-accent text-white px-8 py-3 rounded-lg font-medium transition-colors"
                  >
                    Back to Home
                  </Link>
                </div>
              </div>

            </div>
          </div>
        </div>
      </div>
      <Footer />
    </>
  );
}