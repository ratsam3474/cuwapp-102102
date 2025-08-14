"use client"
import HelixImage from '../assets/images/helix2.png'
import EmojiImage from '../assets/images/emojistar.png'
import Image from 'next/image';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useRef, useEffect, useState } from 'react';

export const CallToAction = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
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

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start end", "end end"]
  })

  const translateY = useTransform(scrollYProgress, [0, 1], [50, -50]);
  
  return (
    <div className="bg-black text-white py-[72px] sm:py-24" ref={containerRef}>
      
      <div className="container max-w-xl relative">
      <motion.div style={{translateY}}>
      <Image src={HelixImage} alt="helix" className="absolute top-6 left-[calc(100%+36px)]" />
      </motion.div>
      <motion.div style={{translateY}}>
       
      <Image src={EmojiImage} alt="emoji" className="absolute -top-[120px] right-[calc(100%+30px)]" />
      </motion.div>
       

        <h2 className="font-bold text-5xl sm:text-6xl tracking-tighter">
          {isLoggedIn ? 'Upgrade Your WhatsApp Marketing' : 'Start Your WhatsApp Journey'}
        </h2>
        <p className="text-xl text-white/70  mt-5">
          {isLoggedIn 
            ? 'Unlock advanced features and grow your business with our premium plans.' 
            : 'Join thousands of businesses automating their WhatsApp marketing with CuWhapp. Get started in minutes.'}
        </p>
        <div className="mt-10 flex flex-col gap-4 max-w-sm mx-auto sm:flex-row">
          {isLoggedIn ? (
            <>
              <a href={`${process.env.NEXT_PUBLIC_API_URL || 'https://app.cuwapp.com'}`} className="bg-brand-primary hover:bg-brand-accent text-white h-12 rounded-lg px-8 flex items-center justify-center font-medium transition-colors sm:flex-1">
                Go to Dashboard
              </a>
              <a href="#pricing" className="bg-white/20 hover:bg-white/30 text-white h-12 rounded-lg px-8 flex items-center justify-center font-medium transition-colors">
                Upgrade Plan
              </a>
            </>
          ) : (
            <>
              <a href={`${process.env.NEXT_PUBLIC_AUTH_URL || 'https://auth.cuwapp.com'}/sign-up`} className="bg-brand-primary hover:bg-brand-accent text-white h-12 rounded-lg px-8 flex items-center justify-center font-medium transition-colors sm:flex-1">
                Start Free Trial
              </a>
              <a href={`${process.env.NEXT_PUBLIC_AUTH_URL || 'https://auth.cuwapp.com'}/sign-in`} className="bg-white/20 hover:bg-white/30 text-white h-12 rounded-lg px-8 flex items-center justify-center font-medium transition-colors">
                View Demo
              </a>
            </>
          )}
        </div>
      </div>


    </div>
  )
};
