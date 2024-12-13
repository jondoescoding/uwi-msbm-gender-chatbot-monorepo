import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const NotFound = () => {
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect to home page after a brief delay
    const timer = setTimeout(() => {
      navigate('/', { replace: true });
    }, 100);

    return () => clearTimeout(timer);
  }, [navigate]);

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-light mb-4">Page Not Found</h1>
        <p className="text-gray-400">Redirecting to home page...</p>
      </div>
    </div>
  );
};

export default NotFound; 