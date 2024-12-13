const Footer = (): JSX.Element => {
  return (
    <footer className="w-full border-t border-white/10 bg-black/60 backdrop-blur-sm py-6">
      <div className="max-w-7xl mx-auto px-8">
        <div className="flex justify-between items-center">
          <div className="text-sm text-gray-400">
            © 2024 MSBM Gender Monitor. All rights reserved.
          </div>
          <div className="text-sm text-gray-400">
            Caribbean Gender News Analysis System
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;