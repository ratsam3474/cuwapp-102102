/**
 * Simple Hyperswitch Checkout Integration
 * Redirects to Hyperswitch for payment processing
 */

async function upgradePlan(planId, price) {
    // Check if user is logged in using cache system
    const user = UserCache.getUser();
    
    if (!user || !user.email || !user.username) {
        // Redirect to login if not authenticated
        alert('Please sign in to upgrade your plan');
        window.location.href = 'https://auth.cuwapp.com/sign-in';
        return;
    }
    
    // Get current plan from app if available
    let currentPlan = 'free';
    if (typeof app !== 'undefined' && app.userSubscription) {
        currentPlan = app.userSubscription.plan_type || 'free';
    }
    
    // Check if it's an upgrade
    const planOrder = ['free', 'starter', 'hobby', 'pro', 'premium'];
    const currentPlanIndex = planOrder.indexOf(currentPlan);
    const selectedPlanIndex = planOrder.indexOf(planId);
    
    if (selectedPlanIndex <= currentPlanIndex) {
        if (selectedPlanIndex === currentPlanIndex) {
            alert(`You are already on the ${planId} plan!`);
        } else {
            alert(`You cannot downgrade from ${currentPlan} to ${planId} plan. Please contact support.`);
        }
        return;
    }
    
    console.log(`User ${user.username} (${user.email}) upgrading from ${currentPlan} to ${planId} plan`);
    
    // Build checkout URL with proper parameters
    const checkoutParams = new URLSearchParams({
        plan: planId,
        amount: price * 100,  // Convert to cents
        email: user.email,
        user_id: user.id || user.username
    });
    
    // Redirect to new direct checkout page with payment method selection
    window.location.href = `/static/checkout-direct.html?${checkoutParams.toString()}`;
}

// Handle payment return
window.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;
    
    if (path === '/payment-success' || path.includes('payment-success')) {
        // Check if we're on the success page
        const urlParams = new URLSearchParams(window.location.search);
        const plan = urlParams.get('plan');
        
        if (plan) {
            // Show success message
            console.log(`Payment successful for ${plan} plan`);
            
            // If we're in the dashboard, refresh to show new plan
            if (typeof app !== 'undefined' && app.loadUserSubscription) {
                setTimeout(() => {
                    app.loadUserSubscription();
                }, 1000);
            }
        }
    }
});