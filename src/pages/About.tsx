import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

const About = () => {
  return (
    <div className="min-h-screen bg-black">
      <Navbar />
      
      <div className="max-w-4xl mx-auto pt-32 px-8 pb-20">
        <div className="space-y-12">
          <div className="space-y-4">
            <div className="text-gray-400 text-sm">About Us</div>
            <h1 className="text-4xl font-light text-white">Understanding Gender Dynamics in the Caribbean</h1>
          </div>

          <div className="space-y-6 text-gray-400">
            <p>
              The Caribbean Gender News Analysis System is a pioneering initiative designed to leverage advanced technology in understanding and analyzing gender-related news and trends across the Caribbean region.
            </p>

            <p>
              Our system employs cutting-edge natural language processing and machine learning techniques to process, analyze, and derive insights from news articles and media coverage related to gender issues in Caribbean countries.
            </p>

            <p>
              Through this platform, researchers, policymakers, and the public can access comprehensive data and analysis about gender-related news, helping to inform decisions and promote understanding of gender dynamics in the Caribbean context.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-6 border border-white/10 rounded-sm">
              <div className="text-2xl text-white mb-4">100+</div>
              <div className="text-gray-400">News Sources Analyzed</div>
            </div>
            <div className="p-6 border border-white/10 rounded-sm">
              <div className="text-2xl text-white mb-4">15+</div>
              <div className="text-gray-400">Caribbean Countries Covered</div>
            </div>
            <div className="p-6 border border-white/10 rounded-sm">
              <div className="text-2xl text-white mb-4">24/7</div>
              <div className="text-gray-400">Real-time Analysis</div>
            </div>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default About;