
"use client";
import MenuIcon from '../assets/icons/menu.svg';
import { UserStatus } from './UserStatus';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';

export const Navbar = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    // Check if user is logged in
    const checkAuth = () => {
      const cached = localStorage.getItem('cuwhapp_user_cache');
      if (cached) {
        try {
          const userData = JSON.parse(cached);
          setIsLoggedIn(userData.isLoggedIn === true);
        } catch (e) {
          setIsLoggedIn(false);
        }
      } else {
        setIsLoggedIn(false);
      }
    };

    checkAuth();
    // Check periodically for auth changes
    const interval = setInterval(checkAuth, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-black">
      <div className="px-4">
    <div className="container bg-black relative">
      <div className="py-4 flex items-center justify-between">

      <Link href="/" className="relative flex items-center gap-3 group">
        <div className='absolute w-full top-2 bottom-0 bg-[linear-gradient(to_right,#1a4d2e,#2d5f3f,#1a4d2e)] blur-md group-hover:blur-lg transition-all'></div>
        {/* Option 1: Just text (current) */}
        <span className="text-white font-bold text-2xl relative group-hover:text-brand-primary transition-colors">CuWhapp</span>
        
        {/* Option 2: With PNG logo - uncomment to use */}
        {/* <Image src="/logo.png" alt="CuWhapp" width={40} height={40} className="relative" />
        <span className="text-white font-bold text-2xl relative group-hover:text-brand-primary transition-colors">CuWhapp</span> */}
      </Link>
      <button 
        onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        className='border border-white border-opacity-30 h-10 w-10 inline-flex justify-center items-center rounded-lg sm:hidden'>
      <MenuIcon className="text-white" />
      </button>
      <nav className='text-white gap-6 items-center hidden sm:flex'>
        
        <a href="/#features" className='text-opacity-60 text-white hover:text-opacity-100 transition' >Features</a>
        <a href="/#pricing" className='text-opacity-60 text-white hover:text-opacity-100 transition'>Pricing</a>
        <a href="/docs" className='text-opacity-60 text-white hover:text-opacity-100 transition'>Docs</a>
        <a href="/blog" className='text-opacity-60 text-white hover:text-opacity-100 transition'>Blog</a>
        <a href="/#faq" className='text-opacity-60 text-white hover:text-opacity-100 transition'>FAQ</a>
        {isLoggedIn && (
          <a href={`${process.env.NEXT_PUBLIC_API_URL || 'https://app.cuwapp.com'}`} className='text-opacity-60 text-white hover:text-opacity-100 transition'>Dashboard</a>
        )}
        <UserStatus />
      </nav>

      </div>

      {/* Mobile Menu Dropdown */}
      {isMobileMenuOpen && (
        <div className="sm:hidden absolute top-full left-0 right-0 bg-black border-t border-white border-opacity-30 z-50">
          <nav className="flex flex-col py-4">
            <a 
              href="/#features" 
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-white text-opacity-60 hover:text-opacity-100 transition px-4 py-3 hover:bg-white hover:bg-opacity-10"
            >
              Features
            </a>
            <a 
              href="/#pricing" 
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-white text-opacity-60 hover:text-opacity-100 transition px-4 py-3 hover:bg-white hover:bg-opacity-10"
            >
              Pricing
            </a>
            <a 
              href="/docs" 
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-white text-opacity-60 hover:text-opacity-100 transition px-4 py-3 hover:bg-white hover:bg-opacity-10"
            >
              Docs
            </a>
            <a 
              href="/blog" 
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-white text-opacity-60 hover:text-opacity-100 transition px-4 py-3 hover:bg-white hover:bg-opacity-10"
            >
              Blog
            </a>
            <a 
              href="/#faq" 
              onClick={() => setIsMobileMenuOpen(false)}
              className="text-white text-opacity-60 hover:text-opacity-100 transition px-4 py-3 hover:bg-white hover:bg-opacity-10"
            >
              FAQ
            </a>
            {isLoggedIn && (
              <a 
                href={`${process.env.NEXT_PUBLIC_API_URL || 'https://app.cuwapp.com'}`}
                onClick={() => setIsMobileMenuOpen(false)}
                className="text-white text-opacity-60 hover:text-opacity-100 transition px-4 py-3 hover:bg-white hover:bg-opacity-10"
              >
                Dashboard
              </a>
            )}
            <div className="px-4 py-3">
              <UserStatus />
            </div>
          </nav>
        </div>
      )}

    </div>
    </div>
    </div>
  )
};
