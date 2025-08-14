/**
 * Unified Checkout Handler for CuWhapp
 * Handles payment upgrades from dashboard and landing page
 */

async function upgradeToplan(planId, price) {
    // Get user from cache
    const user = UserCache.getUser();
    
    if (!user || !user.email) {
        alert('Please sign in to upgrade your plan');
        window.location.href = 'https://auth.cuwapp.com/sign-in';
        return;
    }
    
    // Plan details
    const plans = {
        starter: { name: 'Starter', price: 7 },
        hobby: { name: 'Hobby', price: 20 },
        pro: { name: 'Pro', price: 45 },
        premium: { name: 'Premium', price: 99 }
    };
    
    const plan = plans[planId];
    if (!plan) {
        alert('Invalid plan selected');
        return;
    }
    
    // Create checkout URL with proper parameters
    const checkoutParams = new URLSearchParams({
        plan: planId,
        amount: plan.price * 100,  // Convert to cents
        email: user.email,
        user_id: user.id
    });
    
    // Redirect to checkout page
    window.location.href = `/static/checkout.html?${checkoutParams.toString()}`;
}

// Dashboard upgrade function (called from app.js)
function upgradePlan(planId) {
    const prices = {
        starter: 7,
        hobby: 20,
        pro: 45,
        premium: 99
    };
    
    upgradeToplan(planId, prices[planId]);
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { upgradeToplan, upgradePlan };
}