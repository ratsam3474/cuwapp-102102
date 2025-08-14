
import InstaIcon from '../assets/icons/insta.svg'
import XIcon from '../assets/icons/x-social.svg'
import LinkedInIcon from '../assets/icons/linkedin.svg'
import YoutubeIcon from '../assets/icons/youtube.svg'

export const Footer = () => {
  return(
    <footer className='py-8 bg-black text-white/60 border-t border-white/20'>
    <div className="container">
      <div className='flex flex-col gap-8'>
        {/* Main Footer Content */}
        <div className='grid grid-cols-1 md:grid-cols-4 gap-8'>
          {/* Brand */}
          <div>
            <h3 className='text-white font-bold text-xl mb-3'>CuWhapp</h3>
            <p className='text-sm'>Cursor for WhatsApp - Automate your WhatsApp marketing with AI-powered tools.</p>
          </div>
          
          {/* Quick Links */}
          <div>
            <h4 className='text-white font-semibold mb-3'>Product</h4>
            <ul className='space-y-2 text-sm'>
              <li><a href="/#features" className='hover:text-white transition'>Features</a></li>
              <li><a href="/#pricing" className='hover:text-white transition'>Pricing</a></li>
              <li><a href={`${process.env.NEXT_PUBLIC_API_URL || 'https://app.cuwapp.com'}`} className='hover:text-white transition'>Dashboard</a></li>
              <li><a href="/blog" className='hover:text-white transition'>Blog</a></li>
            </ul>
          </div>
          
          {/* Resources */}
          <div>
            <h4 className='text-white font-semibold mb-3'>Resources</h4>
            <ul className='space-y-2 text-sm'>
              <li><a href="/docs" className='hover:text-white transition'>Documentation</a></li>
              <li><a href="/#faq" className='hover:text-white transition'>FAQ</a></li>
              <li><a href="https://wa.me/17194938889" className='hover:text-white transition'>WhatsApp Support</a></li>
            </ul>
          </div>
          
          {/* Get Started */}
          <div>
            <h4 className='text-white font-semibold mb-3'>Get Started</h4>
            <ul className='space-y-2 text-sm'>
              <li><a href={`${process.env.NEXT_PUBLIC_AUTH_URL || 'https://auth.cuwapp.com'}/sign-up`} className='hover:text-white transition'>Sign Up</a></li>
              <li><a href={`${process.env.NEXT_PUBLIC_AUTH_URL || 'https://auth.cuwapp.com'}/sign-in`} className='hover:text-white transition'>Login</a></li>
              <li><a href={`${process.env.NEXT_PUBLIC_AUTH_URL || 'https://auth.cuwapp.com'}/sign-up`} className='hover:text-white transition'>Free Trial</a></li>
            </ul>
          </div>
        </div>
        
        {/* Bottom Bar */}
        <div className='flex flex-col gap-4 sm:flex-row sm:justify-between pt-6 border-t border-white/10'>
          <div className="text-center sm:text-left text-sm">© 2025 CuWhapp. All rights reserved.</div>
          <div className='flex justify-center gap-6 text-sm'>
            <a href="/privacy-policy" className='hover:text-white transition'>Privacy Policy</a>
            <a href="/terms-of-service" className='hover:text-white transition'>Terms of Service</a>
            <a href="https://wa.me/17194938889" className='hover:text-white transition'>Contact</a>
          </div>
        </div>
      </div>
    </div>
    </footer>
  )
};
