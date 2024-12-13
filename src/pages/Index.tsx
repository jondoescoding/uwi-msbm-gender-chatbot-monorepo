import { Search, MessageSquare } from "lucide-react";
import { Link } from "react-router-dom";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const Index = () => {
  return (
    <div className="min-h-screen bg-black">
      <Navbar />
      
      <div className="pt-32 pb-20 px-8 max-w-7xl mx-auto relative">
        <div className="absolute top-0 right-0 w-96 h-96 opacity-20 pointer-events-none">
          <img src="/spinning-globe.gif" alt="Spinning Globe" className="w-full h-full object-contain" />
        </div>

        <div className="flex flex-col space-y-8">
          <div className="space-y-2">
            <div className="text-gray-400 text-sm">01</div>
            <h1 className="text-6xl font-light text-white leading-tight">
              Caribbean Gender News<br />Analysis System
            </h1>
          </div>

          <p className="text-xl text-gray-400 max-w-2xl font-light">
            This system is designed to analyze and provide insights on gender-related news articles from Caribbean countries.
          </p>

          <p className="text-gray-400 max-w-3xl font-light">
            Our goal is to facilitate research and understanding of gender issues in the Caribbean region through advanced natural language processing and machine learning techniques.
          </p>

          <div className="flex gap-4">
            <Link 
              to="/search" 
              className="px-6 py-3 border border-white/20 text-white hover:bg-white/5 transition-all duration-300 hover:scale-105 hover:border-white/40 rounded-sm"
            >
              KEYWORD SEARCH
            </Link>
            <Link 
              to="/chat" 
              className="px-6 py-3 border border-white/20 text-white hover:bg-white/5 transition-all duration-300 hover:scale-105 hover:border-white/40 rounded-sm"
            >
              CHAT NOW
            </Link>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Index;