import { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const Navbar = (): JSX.Element => {
  const [isOpen, setIsOpen] = useState(false);

  const toggleMenu = () => {
    setIsOpen(!isOpen);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-black/95 backdrop-blur-sm border-b border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="text-xl font-light text-white">
            MSBM Gender Monitor
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex space-x-8">
            <Link to="/search" className="text-gray-400 hover:text-white transition-colors font-light text-sm">
              Keyword Search
            </Link>
            <Link to="/chatbot" className="text-gray-400 hover:text-white transition-colors font-light text-sm">
              Chatbot
            </Link>
            <Link to="/about" className="text-gray-400 hover:text-white transition-colors font-light text-sm">
              About
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={toggleMenu}
            className="md:hidden text-gray-400 hover:text-white transition-colors"
            aria-label="Toggle menu"
          >
            {isOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="md:hidden"
          >
            <div className="px-4 pt-2 pb-4 space-y-2 bg-black/95 backdrop-blur-sm border-b border-gray-800">
              <Link
                to="/search"
                className="block py-2 text-gray-400 hover:text-white transition-colors font-light text-sm"
                onClick={() => setIsOpen(false)}
              >
                Keyword Search
              </Link>
              <Link
                to="/chatbot"
                className="block py-2 text-gray-400 hover:text-white transition-colors font-light text-sm"
                onClick={() => setIsOpen(false)}
              >
                Chatbot
              </Link>
              <Link
                to="/about"
                className="block py-2 text-gray-400 hover:text-white transition-colors font-light text-sm"
                onClick={() => setIsOpen(false)}
              >
                About
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
};

export default Navbar;