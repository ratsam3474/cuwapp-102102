"use client";

import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { useState } from "react";
import { ChevronRight, BookOpen, Zap, Users, MessageSquare, Flame, Download } from "lucide-react";

export default function Documentation() {
  const [activeSection, setActiveSection] = useState("quickstart");

  const sections = [
    {
      id: "quickstart",
      title: "Quick Start",
      icon: <Zap className="w-5 h-5" />,
      description: "Get started with CuWhapp in minutes"
    },
    {
      id: "sessions",
      title: "WhatsApp Sessions",
      icon: <MessageSquare className="w-5 h-5" />,
      description: "Connect and manage WhatsApp sessions"
    },
    {
      id: "campaigns",
      title: "Campaigns",
      icon: <BookOpen className="w-5 h-5" />,
      description: "Create and launch message campaigns"
    },
    {
      id: "group-campaigns",
      title: "Group Campaigns",
      icon: <Users className="w-5 h-5" />,
      description: "Launch campaigns to WhatsApp groups"
    },
    {
      id: "contacts",
      title: "Contact Management",
      icon: <Users className="w-5 h-5" />,
      description: "Manage your leads and contacts"
    },
    {
      id: "group-export",
      title: "Group Export",
      icon: <Download className="w-5 h-5" />,
      description: "Export group participants data"
    },
    {
      id: "warmer",
      title: "WhatsApp Warmer",
      icon: <Flame className="w-5 h-5" />,
      description: "Warm up your WhatsApp accounts"
    }
  ];

  const renderContent = () => {
    switch(activeSection) {
      case "quickstart":
        return (
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl font-bold text-white mb-4">Quick Start Guide</h2>
              <p className="text-gray-400 mb-6">
                Welcome to CuWhapp! This guide will help you get started with creating and launching your first WhatsApp outbound message campaign.
              </p>
            </div>
            
            <div className="bg-gradient-to-br from-gray-900 to-black p-6 rounded-2xl border border-gray-800">
              <h3 className="text-xl font-semibold text-brand-primary mb-4">
                Create and Launch WhatsApp Outbound Message Campaign
              </h3>
              <iframe 
                src="https://scribehow.com/embed/QUICK_START_Create_and_Launch_WhatsApp_Outbound_Message_Campaign__Cb10kAVfQiqg8qF63-ldMg?as=scrollable" 
                width="100%" 
                height="800" 
                allow="fullscreen" 
                style={{ border: 0, minHeight: "640px", borderRadius: "12px" }}
                className="w-full"
              />
            </div>
          </div>
        );
        
      case "sessions":
        return (
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl font-bold text-white mb-4">WhatsApp Sessions</h2>
              <p className="text-gray-400 mb-6">
                Learn how to create and connect to WhatsApp sessions for your automation needs.
              </p>
            </div>
            
            <div className="bg-gradient-to-br from-gray-900 to-black p-6 rounded-2xl border border-gray-800">
              <h3 className="text-xl font-semibold text-brand-primary mb-4">
                Create and Connect to a WhatsApp Session
              </h3>
              <iframe 
                src="https://scribehow.com/embed/Create_and_Connect_to_a_WhatsApp_Session__3w2CGQD2TgOyaNU30awg4w?as=scrollable" 
                width="100%" 
                height="800" 
                allow="fullscreen" 
                style={{ border: 0, minHeight: "640px", borderRadius: "12px" }}
                className="w-full"
              />
            </div>
          </div>
        );
        
      case "campaigns":
        return (
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl font-bold text-white mb-4">Campaigns</h2>
              <p className="text-gray-400 mb-6">
                Learn how to create and launch effective WhatsApp marketing campaigns to reach your audience.
              </p>
            </div>
            
            <div className="bg-gradient-to-br from-gray-900 to-black p-6 rounded-2xl border border-gray-800">
              <h3 className="text-xl font-semibold text-brand-primary mb-4">
                Create and Launch a WhatsApp Campaign
              </h3>
              <iframe 
                src="https://scribehow.com/embed/Create_and_Launch_a_WhatsApp_Campaign__qmfEqkP-TmmIWwMvPZbm_w?as=scrollable" 
                width="100%" 
                height="800" 
                allow="fullscreen" 
                style={{ border: 0, minHeight: "640px", borderRadius: "12px" }}
                className="w-full"
              />
            </div>
          </div>
        );
        
      case "contacts":
        return (
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl font-bold text-white mb-4">Contact Management</h2>
              <p className="text-gray-400 mb-6">
                Efficiently manage your WhatsApp contacts and leads with our powerful tools.
              </p>
            </div>
            
            <div className="bg-gradient-to-br from-gray-900 to-black p-6 rounded-2xl border border-gray-800">
              <h3 className="text-xl font-semibold text-brand-primary mb-4">
                Manage Your Contact Leads
              </h3>
              <iframe 
                src="https://scribehow.com/embed/Manage_your_contact_leads__phD917RkRH-8W8J-2e_LNg?as=scrollable" 
                width="100%" 
                height="800" 
                allow="fullscreen" 
                style={{ border: 0, minHeight: "640px", borderRadius: "12px" }}
                className="w-full"
              />
            </div>
          </div>
        );
        
      case "group-campaigns":
        return (
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl font-bold text-white mb-4">WhatsApp Group Campaigns</h2>
              <p className="text-gray-400 mb-6">
                Learn how to create and launch targeted campaigns to WhatsApp groups for maximum reach and engagement.
              </p>
            </div>
            
            <div className="bg-gradient-to-br from-gray-900 to-black p-6 rounded-2xl border border-gray-800">
              <h3 className="text-xl font-semibold text-brand-primary mb-4">
                Create and Launch WhatsApp Group Campaigns
              </h3>
              <iframe 
                src="https://scribehow.com/embed/Create_and_Launch_WhatsApp_Group_Campaigns__tP26N44LSHOYP8iCd2PbyA?as=scrollable" 
                width="100%" 
                height="800" 
                allow="fullscreen" 
                style={{ border: 0, minHeight: "640px", borderRadius: "12px" }}
                className="w-full"
              />
            </div>
          </div>
        );
        
      case "group-export":
        return (
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl font-bold text-white mb-4">Group Export</h2>
              <p className="text-gray-400 mb-6">
                Extract valuable contact data from WhatsApp groups. Create groups and export participant information for your lead generation efforts.
              </p>
            </div>
            
            <div className="bg-gradient-to-br from-gray-900 to-black p-6 rounded-2xl border border-gray-800">
              <h3 className="text-xl font-semibold text-brand-primary mb-4">
                Create a Group and Export Participants
              </h3>
              <iframe 
                src="https://scribehow.com/embed/Create_a_Group_and_Export_Participants__QIld--sIRY6dpjJGWh2Fxg?as=scrollable" 
                width="100%" 
                height="800" 
                allow="fullscreen" 
                style={{ border: 0, minHeight: "640px", borderRadius: "12px" }}
                className="w-full"
              />
            </div>
          </div>
        );
        
      case "warmer":
        return (
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl font-bold text-white mb-4">WhatsApp Warmer</h2>
              <p className="text-gray-400 mb-6">
                Keep your WhatsApp accounts healthy and avoid restrictions with our warming feature.
              </p>
            </div>
            
            <div className="bg-gradient-to-br from-gray-900 to-black p-6 rounded-2xl border border-gray-800">
              <h3 className="text-xl font-semibold text-brand-primary mb-4">
                Create WhatsApp Warmer Session
              </h3>
              <iframe 
                src="https://scribehow.com/embed/Create_WhatsApp_Warmer_Session__d-zUIQhHQtCnSQWv9pL3xw?as=scrollable" 
                width="100%" 
                height="800" 
                allow="fullscreen" 
                style={{ border: 0, minHeight: "640px", borderRadius: "12px" }}
                className="w-full"
              />
            </div>
          </div>
        );
        
      default:
        return (
          <div className="text-center py-12">
            <p className="text-gray-400">Select a section from the sidebar to view documentation.</p>
          </div>
        );
    }
  };

  return (
    <>
      <div className="overflow-x-hidden">
        <Navbar />
        
        {/* Hero Section */}
        <div className="bg-black text-white bg-[linear-gradient(to_bottom,#000,#0f3d0f_34%,#1a4d2e_65%,#2d5f3f_82%)] py-16 sm:py-24">
          <div className="container">
            <div className="max-w-4xl mx-auto text-center">
              <div className="inline-flex items-center gap-2 bg-brand-primary/20 px-4 py-2 rounded-full mb-6">
                <BookOpen className="w-5 h-5 text-brand-primary" />
                <span className="text-brand-primary font-medium">Documentation</span>
              </div>
              <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-6">
                Learn How to Use CuWhapp
              </h1>
              <p className="text-xl text-gray-400">
                Step-by-step guides to help you master WhatsApp automation and lead generation
              </p>
            </div>
          </div>
        </div>

        {/* Documentation Content */}
        <div className="bg-black text-white py-16 min-h-screen">
          <div className="container">
            <div className="flex flex-col lg:flex-row gap-8">
              
              {/* Sidebar Navigation */}
              <aside className="lg:w-80">
                <div className="sticky top-4">
                  <div className="bg-gradient-to-br from-gray-900 to-black p-6 rounded-2xl border border-gray-800">
                    <h3 className="text-lg font-semibold text-white mb-4">Documentation</h3>
                    <nav className="space-y-2">
                      {sections.map((section) => (
                        <button
                          key={section.id}
                          onClick={() => setActiveSection(section.id)}
                          className={`w-full flex items-start gap-3 p-3 rounded-lg transition-all ${
                            activeSection === section.id
                              ? "bg-brand-primary/20 text-brand-primary border-l-4 border-brand-primary"
                              : "hover:bg-gray-800 text-gray-400 hover:text-white"
                          }`}
                        >
                          <div className="mt-0.5">{section.icon}</div>
                          <div className="text-left">
                            <div className="font-medium">{section.title}</div>
                            <div className="text-xs opacity-70 mt-0.5">{section.description}</div>
                          </div>
                        </button>
                      ))}
                    </nav>
                  </div>

                  {/* Help Card */}
                  <div className="bg-gradient-to-br from-brand-primary/20 to-brand-secondary/20 p-6 rounded-2xl border border-brand-primary/30 mt-6">
                    <h4 className="text-white font-semibold mb-2">Need Help?</h4>
                    <p className="text-gray-300 text-sm mb-4">
                      Can&apos;t find what you&apos;re looking for? Contact our support team.
                    </p>
                    <a 
                      href="https://wa.me/17194938889" 
                      className="inline-flex items-center gap-2 bg-brand-primary hover:bg-brand-accent text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                    >
                      <MessageSquare className="w-4 h-4" />
                      WhatsApp Support
                    </a>
                  </div>
                </div>
              </aside>

              {/* Main Content */}
              <main className="flex-1 max-w-4xl">
                {renderContent()}
                
                {/* Navigation Footer */}
                <div className="flex justify-between items-center mt-12 pt-8 border-t border-gray-800">
                  <button 
                    onClick={() => {
                      const currentIndex = sections.findIndex(s => s.id === activeSection);
                      if (currentIndex > 0) {
                        setActiveSection(sections[currentIndex - 1].id);
                      }
                    }}
                    disabled={activeSection === sections[0].id}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                      activeSection === sections[0].id
                        ? "bg-gray-900 text-gray-600 cursor-not-allowed"
                        : "bg-gray-800 hover:bg-gray-700 text-white"
                    }`}
                  >
                    <ChevronRight className="w-4 h-4 rotate-180" />
                    Previous
                  </button>
                  
                  <button 
                    onClick={() => {
                      const currentIndex = sections.findIndex(s => s.id === activeSection);
                      if (currentIndex < sections.length - 1) {
                        setActiveSection(sections[currentIndex + 1].id);
                      }
                    }}
                    disabled={activeSection === sections[sections.length - 1].id}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                      activeSection === sections[sections.length - 1].id
                        ? "bg-gray-900 text-gray-600 cursor-not-allowed"
                        : "bg-brand-primary hover:bg-brand-accent text-white"
                    }`}
                  >
                    Next
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </main>
            </div>
          </div>
        </div>
      </div>
      <Footer />
    </>
  );
}