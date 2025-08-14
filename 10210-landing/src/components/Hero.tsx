"use client"
import CursorImage from '../assets/images/cursor.png'
import ArrowIcon from '../assets/icons/arrow-w.svg'
import MessageImage from '../assets/images/message.png'
import Image from 'next/image';
import {motion} from 'framer-motion'
import { AnimatedGradientTextDemo } from './animatedtext';
import { useEffect, useState } from 'react';

export const Hero = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

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
    const interval = setInterval(checkAuth, 2000);
    return () => clearInterval(interval);
  }, []);
  return (
    <div className="bg-black text-white bg-[linear-gradient(to_bottom,#000,#0f3d0f_34%,#1a4d2e_65%,#2d5f3f_82%)] py-[72px] sm:py-24 relative overflow-clip">
      <div className="absolute h-[375px] w-[750px] sm:w-[1536px] sm:h-[768px] lg:w-[2400px] llg:h-[800px] rounded-[100%] bg-black left-1/2 -translate-x-1/2 border border-brand-accent bg-[radial-gradient(closest-side,#000_82%,#1a4d2e)] top-[calc(100%-96px)] sm:top-[calc(100%-120px)]"></div>
    <div className="container relative">
      <div className="flex items-center justify-center -mt-10">
        <AnimatedGradientTextDemo/>
      </div>
      <div className="flex justify-center mt-8 ">
      <div className="inline-flex relative">
      <h1 className='text-6xl sm:text-8xl font-bold tracking-tightner text-center'>CuWhapp</h1>
      </div>
      </div>
      <div className="flex justify-center">
      <p className='text-xl text-center mt-8 max-w-2xl'>Easily manage your WhatsApp leads with powerful features like contact download, personalized AI chat assistant, campaign management, WhatsApp warmer, and comprehensive analytics.</p>
      </div>
      <div className="flex justify-center mt-8 gap-4">
      {isLoggedIn ? (
        <>
          <a href={`${process.env.NEXT_PUBLIC_API_URL || 'https://app.cuwapp.com'}`} className='inline-block bg-brand-primary hover:bg-brand-accent text-white py-3 px-6 rounded-lg font-medium transition-colors'>Go to Dashboard</a>
          <a href="#pricing" className='inline-block border border-white text-white py-3 px-6 rounded-lg font-medium hover:bg-white hover:text-black transition-colors'>View Plans</a>
        </>
      ) : (
        <>
          <a href={`${process.env.NEXT_PUBLIC_AUTH_URL || 'https://auth.cuwapp.com'}/sign-up`} className='inline-block bg-brand-primary hover:bg-brand-accent text-white py-3 px-6 rounded-lg font-medium transition-colors'>Get Started Free</a>
          <a href={`${process.env.NEXT_PUBLIC_AUTH_URL || 'https://auth.cuwapp.com'}/sign-in`} className='inline-block border border-white text-white py-3 px-6 rounded-lg font-medium hover:bg-white hover:text-black transition-colors'>View Demo</a>
        </>
      )}
      </div>


    </div>
    

    </div>
  )
};
