/**
 * Compact Payment Integration for CuWhapp
 * Streamlined Hyperswitch integration with multiple payment methods
 */

class CompactPayment {
    constructor() {
        this.hyper = null;
        this.widgets = null;
        this.unifiedCheckout = null;
        this.paymentId = null;
        this.clientSecret = null;
        this.planPrices = {
            starter: 700,   // $7 in cents
            hobby: 2000,    // $20 in cents
            pro: 4500,      // $45 in cents
            premium: 9900   // $99 in cents
        };
        this.planNames = {
            starter: 'Starter Plan',
            hobby: 'Hobby Plan',
            pro: 'Pro Plan',
            premium: 'Premium Plan'
        };
    }

    async init(planId, userId, email) {
        try {
            // Step 1: Create payment intent on server
            const paymentData = await this.createPaymentIntent(planId, userId, email);
            this.clientSecret = paymentData.clientSecret;
            this.paymentId = paymentData.paymentId;
            
            // Step 2: Initialize Hyperswitch
            const publishableKey = 'pk_snd_68a3be601ff24b82a4b163a8b3d046b2';
            this.hyper = Hyper(publishableKey);
            
            // Step 3: Create widgets with styling
            this.widgets = this.hyper.widgets({
                clientSecret: this.clientSecret,
                appearance: {
                    theme: 'default',
                    variables: {
                        colorPrimary: '#667eea',
                        colorBackground: '#ffffff',
                        colorText: '#333333',
                        colorDanger: '#df1b41',
                        borderRadius: '8px',
                        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                    }
                }
            });
            
            // Step 4: Create and mount unified checkout
            await this.mountPaymentWidget(email);
            
            return true;
        } catch (error) {
            console.error('Payment initialization failed:', error);
            throw error;
        }
    }

    async createPaymentIntent(planId, userId, email) {
        const response = await fetch('/api/payments/create-payment-intent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                plan_id: planId,
                amount: this.planPrices[planId],
                user_id: userId,
                email: email,
                currency: 'USD',
                return_url: `${window.location.origin}/static/payment-success.html?plan=${planId}`,
                cancel_url: `${window.location.origin}/static/checkout.html?plan=${planId}`
            })
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Payment creation failed: ${error}`);
        }
        
        const data = await response.json();
        return {
            clientSecret: data.clientSecret || data.client_secret,
            paymentId: data.payment_id
        };
    }

    async mountPaymentWidget(email) {
        // Create unified checkout with all payment methods
        this.unifiedCheckout = this.widgets.create('payment', {
            layout: 'tabs',
            wallets: {
                walletReturnUrl: `${window.location.origin}/static/payment-success.html`,
                applePay: 'auto',    // Auto-detect Apple Pay availability
                googlePay: 'auto',   // Auto-detect Google Pay availability
                payPal: 'auto'       // Enable PayPal
            },
            paymentMethodOrder: ['card', 'wallet', 'bank_transfer', 'crypto'],
            showCardFormByDefault: true,
            defaultValues: {
                billingDetails: {
                    email: email
                }
            }
        });

        // Mount to DOM element
        const mountResult = await this.unifiedCheckout.mount('#payment-widget');
        if (mountResult?.error) {
            throw new Error(mountResult.error.message || 'Failed to mount payment widget');
        }
    }

    async confirmPayment(planId) {
        try {
            // Confirm payment with Hyperswitch
            const result = await this.hyper.confirmPayment({
                elements: this.unifiedCheckout,
                confirmParams: {
                    return_url: `${window.location.origin}/static/payment-success.html?plan=${planId}`
                },
                redirect: 'if_required'
            });

            if (result.error) {
                throw new Error(result.error.message);
            }

            // Handle successful payment without redirect (card payments)
            if (result.status === 'succeeded' || result.status === 'processing') {
                await this.updateSubscription(planId, result.paymentIntent?.id || this.paymentId);
                return { 
                    success: true, 
                    needsRedirect: false, 
                    paymentId: result.paymentIntent?.id || this.paymentId 
                };
            }

            // Payment requires redirect (PayPal, bank transfer, etc.)
            return { success: true, needsRedirect: true };
            
        } catch (error) {
            console.error('Payment confirmation failed:', error);
            throw error;
        }
    }

    async updateSubscription(planId, paymentId) {
        const user = UserCache.getUser();
        if (!user) throw new Error('User not found');
        
        const response = await fetch('/api/users/payment-success', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: user.id,
                plan_type: planId,
                payment_id: paymentId || this.paymentId || `test_${Date.now()}`,
                amount: this.planPrices[planId]
            })
        });

        if (!response.ok) {
            const error = await response.text();
            throw new Error(`Subscription update failed: ${error}`);
        }
        
        return await response.json();
    }

    // Helper method to check payment status
    async checkPaymentStatus(clientSecret) {
        const payment = await this.hyper.retrievePayment(clientSecret);
        return payment;
    }

    // Get plan details
    getPlanDetails(planId) {
        return {
            name: this.planNames[planId],
            price: this.planPrices[planId] / 100,
            priceInCents: this.planPrices[planId]
        };
    }
}

// Export for use in pages
window.CompactPayment = CompactPayment;