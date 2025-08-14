"use client"
import { Check, X } from 'lucide-react';
import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';

const pricingPlans = [
  {
    id: "free",
    name: "Free",
    price: "$0",
    priceValue: 0,
    description: "Perfect for trying out CuWhapp",
    features: [
      { text: "1 WhatsApp session", included: true },
      { text: "100 messages per month", included: true },
      { text: "100 contact exports per month", included: true },
      { text: "WhatsApp Warmer", included: false },
      { text: "Community support", included: true },
    ],
    buttonText: "Start Free",
    popular: false,
  },
  {
    id: "starter",
    name: "Starter",
    price: "$7",
    priceValue: 7,
    description: "Great for small businesses",
    features: [
      { text: "1 WhatsApp session", included: true },  // Updated from 2 to 1
      { text: "1,000 messages per month", included: true },
      { text: "Unlimited contact exports", included: true },
      { text: "WhatsApp Warmer", included: false },  // No warmer - needs min 2 sessions
      { text: "Email support", included: true },
    ],
    buttonText: "Start Starter",
    popular: false,
  },
  {
    id: "hobby",
    name: "Hobby",
    price: "$20",
    priceValue: 20,
    description: "For growing teams",
    features: [
      { text: "3 WhatsApp sessions", included: true },  // Updated from 5 to 3
      { text: "10,000 messages per month", included: true },
      { text: "Unlimited contact exports", included: true },
      { text: "WhatsApp Warmer - 24 hours", included: true },  // Warmer available with 3 sessions
      { text: "Email support", included: true },
    ],
    buttonText: "Start Hobby",
    popular: true,
  },
  {
    id: "pro",
    name: "Pro",
    price: "$45",
    priceValue: 45,
    description: "For scaling businesses",
    features: [
      { text: "10 WhatsApp sessions", included: true },  // Updated from 15 to 10
      { text: "30,000 messages per month", included: true },  // Updated from 50k to 30k
      { text: "Unlimited contact exports", included: true },
      { text: "WhatsApp Warmer - 4 days", included: true },
      { text: "Priority support", included: true },
    ],
    buttonText: "Start Pro",
    popular: false,
  },
  {
    id: "premium",
    name: "Premium",
    price: "$99",
    priceValue: 99,
    description: "For large organizations",
    features: [
      { text: "30 WhatsApp sessions", included: true },  // Updated from 50 to 30
      { text: "Unlimited messages", included: true },
      { text: "Unlimited contact exports", included: true },
      { text: "WhatsApp Warmer - 15 days", included: true },
      { text: "Dedicated support", included: true },
    ],
    buttonText: "Start Premium",
    popular: false,
  },
];

export const CuWhappPricing = () => {
  const [userPlan, setUserPlan] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Check user's current plan
    const checkUserPlan = async () => {
      if (typeof window !== 'undefined') {
        const cachedUser = localStorage.getItem('cuwhapp_user_cache');
        if (cachedUser) {
          try {
            const user = JSON.parse(cachedUser);
            if (user && user.id) {
              // Fetch user's subscription
              const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://app.cuwapp.com'}/api/users/subscription/${user.id}`, {
                headers: {
                  'Authorization': `Bearer ${user.token || 'test_token'}`
                }
              });
              if (response.ok) {
                const subscription = await response.json();
                setUserPlan(subscription.plan_type);
              }
            }
          } catch (e) {
            console.error('Error checking user plan:', e);
          }
        }
      }
    };
    checkUserPlan();
  }, []);

  const handlePlanClick = async (planId: string, priceValue: number) => {
    // Check if user is logged in via cache
    let user = null;
    
    if (typeof window !== 'undefined') {
      // Check unified cache first
      const cachedUser = localStorage.getItem('cuwhapp_user_cache');
      if (cachedUser) {
        try {
          user = JSON.parse(cachedUser);
        } catch (e) {
          console.error('Error parsing user cache:', e);
        }
      }
      
      // Fallback to old cache
      if (!user) {
        const oldCache = localStorage.getItem('whatsapp_agent_user');
        if (oldCache) {
          try {
            user = JSON.parse(oldCache);
          } catch (e) {
            console.error('Error parsing old cache:', e);
          }
        }
      }
    }
    
    // Check if user has email in session
    if (user && user.email && user.id) {
      // User has session with email, go directly to checkout-direct
      console.log(`User ${user.username || user.email} (${user.email}) is selecting plan: ${planId} - Direct checkout`);
      
      // Check if it's the same plan or a downgrade
      const planOrder = ['free', 'starter', 'hobby', 'pro', 'premium'];
      const currentPlanIndex = planOrder.indexOf(userPlan || 'free');
      const selectedPlanIndex = planOrder.indexOf(planId);
      
      if (selectedPlanIndex <= currentPlanIndex) {
        if (selectedPlanIndex === currentPlanIndex) {
          alert(`You are already on the ${planId} plan!`);
        } else {
          alert(`You cannot downgrade from ${userPlan} to ${planId} plan. Please contact support.`);
        }
        return;
      }
      
      // For free plan, still redirect to sign-up
      if (priceValue === 0) {
        window.location.href = `${process.env.NEXT_PUBLIC_AUTH_URL || 'https://auth.cuwapp.com'}/sign-up`;
        return;
      }
      
      // Redirect directly to checkout-direct.html with user details
      const checkoutParams = new URLSearchParams({
        plan: planId,
        amount: String(priceValue * 100), // Convert to cents
        email: user.email,
        user_id: user.id
      });
      
      window.location.href = `${process.env.NEXT_PUBLIC_API_URL || 'https://app.cuwapp.com'}/static/checkout-direct.html?${checkoutParams.toString()}`;
      return;
    }
    
    // No cached user with email, redirect to sign-in page first
    if (!user || !user.email) {
      window.location.href = `${process.env.NEXT_PUBLIC_AUTH_URL || 'https://auth.cuwapp.com'}/sign-in`;
      return;
    }
    
  };

  return (
    <div className="bg-black text-white py-24" id="pricing">
      <div className="container">
        <div className="text-center mb-16">
          <h2 className="text-5xl font-bold mb-4">
            Simple, Transparent Pricing
          </h2>
          <p className="text-xl text-gray-400">
            Choose the perfect plan for your WhatsApp marketing needs
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          {pricingPlans.map((plan, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`relative rounded-2xl p-6 ${
                plan.popular
                  ? 'bg-gradient-to-br from-brand-primary to-brand-secondary border-2 border-brand-primary'
                  : 'bg-gradient-to-br from-gray-900 to-black border border-gray-800'
              }`}
            >
              {plan.popular && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <span className="bg-brand-primary text-white px-3 py-1 rounded-full text-sm font-semibold">
                    MOST POPULAR
                  </span>
                </div>
              )}

              <div className="mb-6">
                <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                <div className="mb-2">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  {plan.price !== "$0" && (
                    <span className="text-gray-400">/month</span>
                  )}
                </div>
                <p className="text-sm text-gray-400">{plan.description}</p>
              </div>

              <ul className="space-y-3 mb-6">
                {plan.features.map((feature, featureIndex) => (
                  <li key={featureIndex} className="flex items-start">
                    {feature.included ? (
                      <Check className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                    ) : (
                      <X className="w-5 h-5 text-red-500 mr-2 flex-shrink-0 mt-0.5" />
                    )}
                    <span className={`text-sm ${feature.included ? 'text-gray-300' : 'text-gray-500'}`}>
                      {feature.text}
                    </span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handlePlanClick(plan.id, plan.priceValue)}
                disabled={!!(userPlan === plan.id || (userPlan && ['free', 'starter', 'hobby', 'pro', 'premium'].indexOf(plan.id) <= ['free', 'starter', 'hobby', 'pro', 'premium'].indexOf(userPlan)))}
                className={`w-full py-3 px-4 rounded-lg font-semibold transition-all ${
                  userPlan === plan.id 
                    ? 'bg-gray-600 text-white cursor-not-allowed opacity-75'
                    : (userPlan && ['free', 'starter', 'hobby', 'pro', 'premium'].indexOf(plan.id) < ['free', 'starter', 'hobby', 'pro', 'premium'].indexOf(userPlan))
                    ? 'bg-gray-500 text-gray-300 cursor-not-allowed opacity-50'
                    : plan.popular
                    ? 'bg-white text-black hover:bg-gray-200'
                    : 'bg-brand-primary text-white hover:bg-brand-accent'
                }`}
              >
                {userPlan === plan.id ? 'Current Plan' : 
                 (userPlan && ['free', 'starter', 'hobby', 'pro', 'premium'].indexOf(plan.id) < ['free', 'starter', 'hobby', 'pro', 'premium'].indexOf(userPlan)) ? 'Downgrade Not Available' :
                 plan.buttonText}
              </button>
            </motion.div>
          ))}
        </div>

        <div className="mt-16 text-center">
          <p className="text-gray-400 mb-4">
            All plans include: Unlimited campaigns, SSL encryption, 99.9% uptime, and regular updates
          </p>
          <p className="text-sm text-gray-500">
            No setup fees. Cancel anytime. Prices in USD.
          </p>
        </div>

        {/* API Access Button */}
        <div className="mt-12 text-center">
          <div className="bg-gradient-to-br from-purple-900 to-black border border-purple-600 rounded-2xl p-8 max-w-2xl mx-auto">
            <h3 className="text-2xl font-bold mb-3 text-white">Need API Access for Unlimited Features?</h3>
            <p className="text-gray-400 mb-6">
              Get custom solutions, unlimited sessions, and dedicated infrastructure for your enterprise needs.
            </p>
            <a 
              href="https://wa.me/17194938889?text=Hi,%20I'm%20interested%20in%20API%20access%20for%20unlimited%20features"
              className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-8 py-4 rounded-lg font-semibold transition-all text-lg"
              target="_blank"
              rel="noopener noreferrer"
            >
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.149-.67.149-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414-.074-.123-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
              </svg>
              Let&apos;s Talk on WhatsApp
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};