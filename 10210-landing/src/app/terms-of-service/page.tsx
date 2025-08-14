import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import Link from "next/link";

export default function TermsOfService() {
  return (
    <>
      <div className="overflow-x-hidden">
        <Navbar />
        
        {/* Hero Section */}
        <div className="bg-black text-white bg-[linear-gradient(to_bottom,#000,#0f3d0f_34%,#1a4d2e_65%,#2d5f3f_82%)] py-16 sm:py-24">
          <div className="container">
            <div className="max-w-4xl mx-auto text-center">
              <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-6">
                Terms of Service
              </h1>
              <p className="text-xl text-gray-400">
                Please read these terms carefully before using CuWhapp services.
              </p>
              <p className="text-sm text-gray-500 mt-4">
                Effective Date: January 2025
              </p>
            </div>
          </div>
        </div>

        {/* Content Section */}
        <div className="bg-black text-white py-16">
          <div className="container">
            <div className="max-w-4xl mx-auto space-y-8">
              
              {/* Agreement to Terms */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-4 text-brand-primary">1. Agreement to Terms</h2>
                <p className="text-gray-300 leading-relaxed">
                  By accessing or using CuWhapp&apos;s WhatsApp automation and lead generation platform (&ldquo;Service&rdquo;), you agree to be bound by these Terms of Service (&ldquo;Terms&rdquo;). If you disagree with any part of these terms, you may not access the Service.
                </p>
              </div>

              {/* Service Description */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">2. Service Description</h2>
                
                <p className="text-gray-300 mb-6">CuWhapp provides:</p>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-black/50 p-4 rounded-lg border border-gray-700">
                    <div className="text-green-500 text-2xl mb-2">📱</div>
                    <h4 className="font-semibold text-white mb-2">WhatsApp Automation</h4>
                    <p className="text-gray-400 text-sm">Automated messaging and campaign management</p>
                  </div>
                  <div className="bg-black/50 p-4 rounded-lg border border-gray-700">
                    <div className="text-green-500 text-2xl mb-2">👥</div>
                    <h4 className="font-semibold text-white mb-2">Lead Generation</h4>
                    <p className="text-gray-400 text-sm">Extract and manage WhatsApp group contacts</p>
                  </div>
                  <div className="bg-black/50 p-4 rounded-lg border border-gray-700">
                    <div className="text-green-500 text-2xl mb-2">🤖</div>
                    <h4 className="font-semibold text-white mb-2">AI Assistant</h4>
                    <p className="text-gray-400 text-sm">Personalized AI-powered chat responses</p>
                  </div>
                  <div className="bg-black/50 p-4 rounded-lg border border-gray-700">
                    <div className="text-green-500 text-2xl mb-2">📊</div>
                    <h4 className="font-semibold text-white mb-2">Analytics</h4>
                    <p className="text-gray-400 text-sm">Campaign performance and engagement tracking</p>
                  </div>
                </div>
              </div>

              {/* Account Terms */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">3. Account Terms</h2>
                
                <div className="space-y-4">
                  <div className="flex items-start">
                    <span className="text-green-500 mr-3 mt-1">✓</span>
                    <div>
                      <h4 className="font-semibold text-white mb-1">Account Creation</h4>
                      <p className="text-gray-300 text-sm">You must provide accurate and complete information when creating an account</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start">
                    <span className="text-green-500 mr-3 mt-1">✓</span>
                    <div>
                      <h4 className="font-semibold text-white mb-1">Account Security</h4>
                      <p className="text-gray-300 text-sm">You are responsible for maintaining the security of your account credentials</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start">
                    <span className="text-green-500 mr-3 mt-1">✓</span>
                    <div>
                      <h4 className="font-semibold text-white mb-1">Age Requirement</h4>
                      <p className="text-gray-300 text-sm">You must be at least 18 years old to use our Service</p>
                    </div>
                  </div>
                  
                  <div className="flex items-start">
                    <span className="text-green-500 mr-3 mt-1">✓</span>
                    <div>
                      <h4 className="font-semibold text-white mb-1">Account Responsibility</h4>
                      <p className="text-gray-300 text-sm">You are responsible for all activities under your account</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Acceptable Use */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">4. Acceptable Use Policy</h2>
                
                <p className="text-gray-300 mb-6">You agree NOT to use CuWhapp to:</p>
                
                <div className="space-y-3">
                  <div className="flex items-start p-3 bg-red-900/20 rounded-lg border border-red-900/50">
                    <span className="text-red-500 mr-3">⚠️</span>
                    <p className="text-gray-300">Send spam or unsolicited messages</p>
                  </div>
                  <div className="flex items-start p-3 bg-red-900/20 rounded-lg border border-red-900/50">
                    <span className="text-red-500 mr-3">⚠️</span>
                    <p className="text-gray-300">Violate WhatsApp&apos;s Terms of Service or Business Terms</p>
                  </div>
                  <div className="flex items-start p-3 bg-red-900/20 rounded-lg border border-red-900/50">
                    <span className="text-red-500 mr-3">⚠️</span>
                    <p className="text-gray-300">Transmit malware, viruses, or harmful code</p>
                  </div>
                  <div className="flex items-start p-3 bg-red-900/20 rounded-lg border border-red-900/50">
                    <span className="text-red-500 mr-3">⚠️</span>
                    <p className="text-gray-300">Harass, abuse, or harm another person or group</p>
                  </div>
                  <div className="flex items-start p-3 bg-red-900/20 rounded-lg border border-red-900/50">
                    <span className="text-red-500 mr-3">⚠️</span>
                    <p className="text-gray-300">Violate any applicable laws or regulations</p>
                  </div>
                </div>
              </div>

              {/* Payment Terms */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">5. Payment & Billing</h2>
                
                <div className="space-y-6">
                  <div>
                    <h3 className="text-xl font-semibold mb-3 text-white">Subscription Plans</h3>
                    <ul className="space-y-2 text-gray-300">
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Monthly and annual billing options available
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        All plans include unlimited campaigns
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Pricing subject to change with 30 days notice
                      </li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold mb-3 text-white">Payment Processing</h3>
                    <ul className="space-y-2 text-gray-300">
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Payments processed securely via Stripe
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Cryptocurrency payments accepted
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">•</span>
                        Auto-renewal unless cancelled before billing period ends
                      </li>
                    </ul>
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold mb-3 text-white">Refund Policy</h3>
                    <p className="text-gray-300">
                      We offer a 7-day money-back guarantee for first-time subscribers. No refunds for partial months or after the guarantee period.
                    </p>
                  </div>
                </div>
              </div>

              {/* Service Limitations */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">6. Service Limitations</h2>
                
                <div className="space-y-4">
                  <div className="border-l-4 border-yellow-500 pl-4">
                    <h4 className="font-semibold text-white">Message Limits</h4>
                    <p className="text-gray-400 text-sm mt-1">
                      Up to 3,000 messages per day based on your subscription plan
                    </p>
                  </div>
                  <div className="border-l-4 border-yellow-500 pl-4">
                    <h4 className="font-semibold text-white">WhatsApp Sessions</h4>
                    <p className="text-gray-400 text-sm mt-1">
                      Number of concurrent WhatsApp sessions based on plan tier
                    </p>
                  </div>
                  <div className="border-l-4 border-yellow-500 pl-4">
                    <h4 className="font-semibold text-white">API Rate Limits</h4>
                    <p className="text-gray-400 text-sm mt-1">
                      Subject to WhatsApp Business API rate limitations
                    </p>
                  </div>
                  <div className="border-l-4 border-yellow-500 pl-4">
                    <h4 className="font-semibold text-white">Fair Use Policy</h4>
                    <p className="text-gray-400 text-sm mt-1">
                      Excessive usage may result in temporary restrictions
                    </p>
                  </div>
                </div>
              </div>

              {/* Intellectual Property */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">7. Intellectual Property</h2>
                
                <div className="space-y-4 text-gray-300">
                  <p>
                    <strong className="text-white">Our Property:</strong> All CuWhapp content, features, and functionality are owned by CuWhapp Technologies and protected by international copyright, trademark, and other intellectual property laws.
                  </p>
                  <p>
                    <strong className="text-white">Your Content:</strong> You retain ownership of content you upload but grant us a license to use it for providing and improving our services.
                  </p>
                  <p>
                    <strong className="text-white">Feedback:</strong> Any feedback or suggestions you provide become our property and may be used without compensation.
                  </p>
                </div>
              </div>

              {/* Disclaimer & Limitation of Liability */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">8. Disclaimer & Limitation of Liability</h2>
                
                <div className="bg-yellow-900/20 border border-yellow-600/50 rounded-lg p-6 mb-6">
                  <h3 className="text-xl font-semibold mb-3 text-yellow-500">⚠️ Important Notice</h3>
                  <p className="text-gray-300 text-sm leading-relaxed">
                    THE SERVICE IS PROVIDED &ldquo;AS IS&rdquo; WITHOUT WARRANTIES OF ANY KIND. WE DO NOT GUARANTEE UNINTERRUPTED SERVICE, ACCURACY, OR ERROR-FREE OPERATION.
                  </p>
                </div>
                
                <p className="text-gray-300 leading-relaxed">
                  To the maximum extent permitted by law, CuWhapp shall not be liable for any indirect, incidental, special, consequential, or punitive damages, including loss of profits, data, or business opportunities.
                </p>
              </div>

              {/* Termination */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">9. Termination</h2>
                
                <div className="space-y-4">
                  <div>
                    <h3 className="text-xl font-semibold mb-2 text-white">By You</h3>
                    <p className="text-gray-300">
                      You may terminate your account at any time through your account settings or by contacting support.
                    </p>
                  </div>
                  
                  <div>
                    <h3 className="text-xl font-semibold mb-2 text-white">By Us</h3>
                    <p className="text-gray-300">
                      We may suspend or terminate your account for violations of these Terms, non-payment, or extended inactivity.
                    </p>
                  </div>
                  
                  <div>
                    <h3 className="text-xl font-semibold mb-2 text-white">Effect of Termination</h3>
                    <p className="text-gray-300">
                      Upon termination, your right to use the Service ceases immediately. Some provisions of these Terms survive termination.
                    </p>
                  </div>
                </div>
              </div>

              {/* Governing Law */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">10. Governing Law</h2>
                <p className="text-gray-300 leading-relaxed">
                  These Terms are governed by the laws of the United States and the State of New York, without regard to conflict of law principles. Any disputes shall be resolved in the courts of New York County, New York.
                </p>
              </div>

              {/* Changes to Terms */}
              <div className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">11. Changes to Terms</h2>
                <p className="text-gray-300 leading-relaxed">
                  We reserve the right to modify these Terms at any time. Material changes will be notified via email or platform notification at least 30 days before taking effect. Continued use after changes constitutes acceptance.
                </p>
              </div>

              {/* Contact Information */}
              <div className="bg-gradient-to-br from-brand-primary/20 to-brand-secondary/20 p-8 rounded-2xl border border-brand-primary/30">
                <h2 className="text-3xl font-bold mb-6 text-brand-primary">12. Contact Information</h2>
                <p className="text-gray-300 leading-relaxed mb-6">
                  For questions about these Terms of Service, please contact us:
                </p>
                <div className="space-y-3">
                  <p className="text-white">
                    <span className="text-gray-400">Email:</span> legal@cuwhapp.com
                  </p>
                  <p className="text-white">
                    <span className="text-gray-400">Support:</span> support@cuwapp.com
                  </p>
                  <p className="text-white">
                    <span className="text-gray-400">WhatsApp:</span> +1 (719) 493-8889
                  </p>
                </div>
              </div>

              {/* Agreement Acknowledgment */}
              <div className="bg-gradient-to-br from-green-900/20 to-green-800/20 p-8 rounded-2xl border border-green-600/50">
                <div className="text-center">
                  <div className="text-4xl mb-4">✅</div>
                  <h3 className="text-2xl font-bold mb-4 text-green-400">By Using CuWhapp</h3>
                  <p className="text-gray-300 leading-relaxed">
                    You acknowledge that you have read, understood, and agree to be bound by these Terms of Service and our Privacy Policy.
                  </p>
                </div>
              </div>

              {/* Navigation */}
              <div className="text-center py-8 border-t border-gray-800">
                <p className="text-gray-400 mb-6">
                  Last updated: January 2025
                </p>
                <div className="flex justify-center gap-4">
                  <Link 
                    href="/privacy-policy"
                    className="inline-block bg-gray-800 hover:bg-gray-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
                  >
                    Privacy Policy
                  </Link>
                  <Link 
                    href="/"
                    className="inline-block bg-brand-primary hover:bg-brand-accent text-white px-6 py-3 rounded-lg font-medium transition-colors"
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