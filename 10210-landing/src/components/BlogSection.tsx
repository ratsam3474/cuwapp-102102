"use client"
import { ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

export const BlogSection = () => {
  return (
    <div className="bg-black text-white py-24" id="blog">
      <div className="container">
        <div className="text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-5xl font-bold mb-4">
              Learn WhatsApp Marketing
            </h2>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-8">
              Expert insights, tutorials, and best practices for WhatsApp marketing success
            </p>
            <a 
              href="https://cuwapp.com/blog" 
              className="inline-flex items-center gap-2 bg-brand-primary hover:bg-brand-accent text-white py-3 px-8 rounded-lg font-semibold transition-all transform hover:scale-105"
            >
              Visit Our Blog
              <ArrowRight className="w-5 h-5" />
            </a>
          </motion.div>
        </div>
      </div>
    </div>
  );
};