#!/bin/bash

# Fix hardcoded URLs in the source code before rebuilding

echo "🔧 Fixing hardcoded localhost URLs..."

# Fix 10210-auth files
sed -i '' 's|https://app.cuwapp.com|/dashboard|g' /Users/JE/documents/102102/10210-auth/app/sync-session/page.tsx
sed -i '' 's|https://app.cuwapp.com|/dashboard|g' /Users/JE/documents/102102/10210-auth/app/user-profile/[[...user-profile]]/page.tsx
sed -i '' 's|https://app.cuwapp.com|/dashboard|g' /Users/JE/documents/102102/10210-auth/app/auth-callback/page.tsx

# Fix 10210-landing files
sed -i '' 's|https://auth.cuwapp.com|/auth|g' /Users/JE/documents/102102/10210-landing/src/app/auth-success/page.tsx
sed -i '' 's|https://auth.cuwapp.com|/auth|g' /Users/JE/documents/102102/10210-landing/src/components/Hero.tsx
sed -i '' 's|https://auth.cuwapp.com|/auth|g' /Users/JE/documents/102102/10210-landing/src/components/Banner.tsx
sed -i '' 's|https://auth.cuwapp.com|/auth|g' /Users/JE/documents/102102/10210-landing/src/components/Footer.tsx
sed -i '' 's|https://auth.cuwapp.com|/auth|g' /Users/JE/documents/102102/10210-landing/src/components/CallToAction.tsx
sed -i '' 's|https://auth.cuwapp.com|/auth|g' /Users/JE/documents/102102/10210-landing/src/components/CuWhappPricing.tsx
sed -i '' 's|https://auth.cuwapp.com|/auth|g' /Users/JE/documents/102102/10210-landing/src/components/UserStatus.tsx

# Fix redirect URL in UserStatus
sed -i '' "s|'https://www.cuwapp.com'|window.location.origin|g" /Users/JE/documents/102102/10210-landing/src/components/UserStatus.tsx

echo "✅ URLs fixed!"