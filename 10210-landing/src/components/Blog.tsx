"use client"
import { Calendar, User, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

const blogPosts = [
  {
    title: "10 WhatsApp Marketing Strategies That Actually Work in 2024",
    excerpt: "Discover proven strategies to boost your WhatsApp marketing ROI and engage customers effectively.",
    author: "Sarah Johnson",
    date: "Dec 15, 2024",
    readTime: "5 min read",
    category: "Marketing",
    image: "https://images.unsplash.com/photo-1611162617474-5b21e879e113?w=500&h=300&fit=crop"
  },
  {
    title: "How to Warm Up Your WhatsApp Account Safely",
    excerpt: "Learn the best practices for warming up WhatsApp accounts to avoid restrictions and improve deliverability.",
    author: "Mike Chen",
    date: "Dec 12, 2024",
    readTime: "7 min read",
    category: "Tutorial",
    image: "https://images.unsplash.com/photo-1633354406259-d70a32cda009?w=500&h=300&fit=crop"
  },
  {
    title: "WhatsApp Business API vs Regular WhatsApp: Complete Guide",
    excerpt: "Understanding the differences and choosing the right solution for your business needs.",
    author: "Emily Davis",
    date: "Dec 10, 2024",
    readTime: "10 min read",
    category: "Guide",
    image: "https://images.unsplash.com/photo-1614680376593-902f74cf0d41?w=500&h=300&fit=crop"
  },
  {
    title: "Maximizing ROI with WhatsApp Campaign Analytics",
    excerpt: "Deep dive into metrics that matter and how to optimize your WhatsApp campaigns for better results.",
    author: "David Park",
    date: "Dec 8, 2024",
    readTime: "6 min read",
    category: "Analytics",
    image: "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=500&h=300&fit=crop"
  },
  {
    title: "Building Customer Relationships Through WhatsApp",
    excerpt: "Transform one-time buyers into loyal customers using personalized WhatsApp communication.",
    author: "Lisa Brown",
    date: "Dec 5, 2024",
    readTime: "8 min read",
    category: "Customer Success",
    image: "https://images.unsplash.com/photo-1556745757-8d76bdb6984b?w=500&h=300&fit=crop"
  },
  {
    title: "WhatsApp Group Management: Best Practices for 2024",
    excerpt: "Effectively manage and grow your WhatsApp groups while maintaining engagement and quality.",
    author: "James Wilson",
    date: "Dec 3, 2024",
    readTime: "5 min read",
    category: "Management",
    image: "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=500&h=300&fit=crop"
  }
];

const categories = ["All", "Marketing", "Tutorial", "Guide", "Analytics", "Customer Success", "Management"];

export const Blog = () => {
  return (
    <div className="bg-black text-white py-24" id="blog">
      <div className="container">
        <div className="text-center mb-16">
          <h2 className="text-5xl font-bold mb-4">
            Latest from CuWhapp Blog
          </h2>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Expert insights, tutorials, and best practices for WhatsApp marketing success
          </p>
        </div>

        {/* Category Filter */}
        <div className="flex flex-wrap justify-center gap-3 mb-12">
          {categories.map((category, index) => (
            <button
              key={index}
              className={`px-4 py-2 rounded-full border transition-all ${
                index === 0
                  ? 'bg-brand-primary border-brand-primary text-white'
                  : 'border-gray-700 text-gray-400 hover:border-brand-primary hover:text-white'
              }`}
            >
              {category}
            </button>
          ))}
        </div>

        {/* Blog Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {blogPosts.map((post, index) => (
            <motion.article
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-gradient-to-br from-gray-900 to-black rounded-2xl overflow-hidden border border-gray-800 hover:border-brand-primary transition-all duration-300 group cursor-pointer"
            >
              {/* Image */}
              <div className="relative h-48 overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={post.image}
                  alt={post.title}
                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                />
                <div className="absolute top-4 left-4">
                  <span className="bg-brand-primary text-white px-3 py-1 rounded-full text-xs font-semibold">
                    {post.category}
                  </span>
                </div>
              </div>

              {/* Content */}
              <div className="p-6">
                <h3 className="text-xl font-bold mb-2 group-hover:text-brand-primary transition-colors">
                  {post.title}
                </h3>
                <p className="text-gray-400 mb-4 text-sm line-clamp-2">
                  {post.excerpt}
                </p>

                {/* Meta */}
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3" />
                      {post.author}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      {post.date}
                    </span>
                  </div>
                  <span>{post.readTime}</span>
                </div>

                {/* Read More */}
                <div className="mt-4 flex items-center text-brand-primary font-semibold text-sm group-hover:gap-2 transition-all">
                  Read More <ArrowRight className="w-4 h-4 ml-1" />
                </div>
              </div>
            </motion.article>
          ))}
        </div>

        {/* Newsletter CTA */}
        <div className="mt-20 text-center">
          <div className="bg-gradient-to-r from-brand-primary to-brand-secondary rounded-2xl p-12 max-w-4xl mx-auto">
            <h3 className="text-3xl font-bold mb-4">
              Get WhatsApp Marketing Tips Weekly
            </h3>
            <p className="text-lg mb-8 text-gray-200">
              Join 10,000+ marketers receiving exclusive WhatsApp marketing insights
            </p>
            <div className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
              <input
                type="email"
                placeholder="Enter your email"
                className="flex-1 px-4 py-3 rounded-lg bg-white/10 border border-white/20 text-white placeholder-gray-400 focus:outline-none focus:border-white"
              />
              <button className="px-6 py-3 bg-white text-black rounded-lg font-semibold hover:bg-gray-200 transition-colors">
                Subscribe
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};