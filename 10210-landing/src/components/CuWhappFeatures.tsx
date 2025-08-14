import { 
  Download, 
  Bot, 
  BarChart3, 
  Users, 
  Megaphone,
  Flame
} from 'lucide-react';

const features = [
  {
    icon: <Download className="w-8 h-8" />,
    title: "WhatsApp Group Contact Download",
    description: "Export all your WhatsApp group contacts with a single click. Organize and manage your leads efficiently."
  },
  {
    icon: <Bot className="w-8 h-8" />,
    title: "Personalized AI Chat Assistant",
    description: "Leverage AI to automate responses and provide personalized interactions with your WhatsApp contacts."
  },
  {
    icon: <Megaphone className="w-8 h-8" />,
    title: "Campaign Management",
    description: "Create, schedule, and manage WhatsApp marketing campaigns with advanced targeting and personalization."
  },
  {
    icon: <Flame className="w-8 h-8" />,
    title: "WhatsApp Warmer",
    description: "Warm up your WhatsApp accounts naturally to improve deliverability and avoid restrictions."
  },
  {
    icon: <BarChart3 className="w-8 h-8" />,
    title: "Comprehensive Analytics",
    description: "Track message delivery, engagement rates, and campaign performance with detailed analytics dashboard."
  },
  {
    icon: <Users className="w-8 h-8" />,
    title: "Contact Management",
    description: "Organize contacts with tags, segments, and custom fields for targeted messaging."
  }
];

export const CuWhappFeatures = () => {
  return (
    <div className="bg-black text-white py-24" id="features">
      <div className="container">
        <div className="text-center mb-16">
          <h2 className="text-5xl font-bold mb-4">
            Everything You Need to <span className="text-brand-primary">Scale</span> Your WhatsApp Marketing
          </h2>
          <p className="text-xl text-gray-400 max-w-3xl mx-auto">
            CuWhapp provides all the tools you need for lead generation, management, automation, and growth of your WhatsApp business communication. Transform your WhatsApp into a powerful lead generation machine.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div
              key={index}
              className="bg-gradient-to-br from-gray-900 to-black p-8 rounded-2xl border border-gray-800 hover:border-brand-primary transition-all duration-300 hover:scale-105"
            >
              <div className="text-brand-primary mb-4">{feature.icon}</div>
              <h3 className="text-2xl font-semibold mb-3">{feature.title}</h3>
              <p className="text-gray-400">{feature.description}</p>
            </div>
          ))}
        </div>

        <div className="mt-16 text-center">
          <p className="text-xl text-gray-400 mb-8">
            Ready to transform your WhatsApp marketing?
          </p>
          <button className="bg-brand-primary hover:bg-brand-accent text-white px-8 py-4 rounded-lg text-lg font-semibold transition-colors">
            Start Your Free Trial
          </button>
        </div>
      </div>
    </div>
  );
};