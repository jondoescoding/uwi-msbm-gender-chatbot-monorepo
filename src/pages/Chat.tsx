import { useState } from "react";
import axios from "axios";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Send, Loader2 } from "lucide-react";
import ReactMarkdown from 'react-markdown';

interface Message {
  type: 'user' | 'bot';
  content: string;
}

interface ChatSource {
  title: string;
  link: string;
  source: string;
  date: string;
}

interface ChatResponse {
  response: string;
  sources: ChatSource[];
  conversation_id: string;
}

const Chat = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      type: 'bot',
      content: 'Hello! I can help you analyze gender-related news and trends in the Caribbean. What would you like to know?'
    }
  ]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Configure axios base URL and instance
  const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL,
    timeout: 60000, // Increase timeout to 60 seconds
    headers: {
      'Content-Type': 'application/json'
    },
    withCredentials: true
  });

  // Add request interceptor for debugging
  api.interceptors.request.use(request => {
    if (import.meta.env.VITE_ENABLE_LOGGING === 'true') {
      console.log('🟦 [Frontend] Request:', {
        url: request.url,
        method: request.method,
        baseURL: request.baseURL,
        headers: request.headers,
        origin: window.location.origin
      });
    }
    return request;
  });

  // Add response interceptor with retry logic
  api.interceptors.response.use(
    response => {
      if (import.meta.env.VITE_ENABLE_LOGGING === 'true') {
        console.log('🟦 [Frontend] Response:', {
          status: response.status,
          data: response.data,
          headers: response.headers
        });
      }
      return response;
    },
    async error => {
      const config = error.config;

      // If there's no retry config or we've reached max retries, throw the error
      if (!config || !config.retry || config._retryCount >= config.retry) {
        console.error('🔴 [Frontend] API Error:', {
          message: error.message,
          response: error.response?.data,
          status: error.response?.status,
          config: {
            url: error.config?.url,
            method: error.config?.method,
            baseURL: error.config?.baseURL
          }
        });
        return Promise.reject(error);
      }

      // Increment retry count
      config._retryCount = config._retryCount || 0;
      config._retryCount += 1;

      // Create new promise with exponential backoff
      const backoff = Math.min(1000 * (Math.pow(2, config._retryCount) - 1), 10000);
      await new Promise(resolve => setTimeout(resolve, backoff));

      // Log retry attempt
      console.log(`🔄 [Frontend] Retrying request (${config._retryCount}/${config.retry})`);

      // Return the retry request
      return api(config);
    }
  );

  // Log the current environment (helpful for debugging)
  console.log('🟦 [Frontend] Current environment:', import.meta.env.VITE_ENV);
  console.log('🟦 [Frontend] API URL:', import.meta.env.VITE_API_URL);

  // Format the response with sources
  const formatResponse = (response: ChatResponse) => {
    const answer = response.response;
    const sourcesList = response.sources.length > 0 
      ? '\n\nSources:\n\n' + response.sources.map(source => {
          const date = new Date(source.date).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
          });
          return `[${source.title} (${source.source}, ${date})](${source.link})`;
        }).join('\n\n')
      : '';
    
    return answer.replace(/\n*Sources:[\s\S]*$/, '') + sourcesList;
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    try {
      setIsLoading(true);
      console.log('🟦 [Frontend] Starting request processing');
      console.log('🟦 [Frontend] User input:', input);

      // Add user message immediately
      setMessages(prev => [...prev, { type: 'user', content: input }]);
      
      // Prepare the chat messages for the API
      const chatMessages = messages.map(msg => ({
        role: msg.type === 'user' ? 'user' : 'assistant',
        content: msg.content
      }));
      
      // Add the current input
      chatMessages.push({
        role: 'user',
        content: input
      });

      // Clear input field
      setInput('');

      // Make API request with correct configuration
      const response = await api.post('/chatbot/chat', {
        messages: chatMessages,
        conversation_id: conversationId
      }, {
        timeout: 60000 // 60 second timeout
      });

      // Format and add bot response
      const formattedResponse = formatResponse(response.data);
      setMessages(prev => [...prev, { type: 'bot', content: formattedResponse }]);
      
      // Store conversation ID if it's new
      if (!conversationId && response.data.conversation_id) {
        setConversationId(response.data.conversation_id);
      }

    } catch (error) {
      console.error("🔴 [Frontend] Error:", error);
      let errorMessage = 'Sorry, something went wrong. Please try again.';
      
      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNABORTED') {
          errorMessage = 'The request took too long to complete. Please try again.';
        } else if (error.response) {
          errorMessage = `Error: ${error.response.data.detail || error.message}`;
        } else if (error.request) {
          errorMessage = 'Error: Could not connect to the server. Please check your connection.';
        }
      }
      
      setMessages(prev => [...prev, { 
        type: 'bot', 
        content: errorMessage
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black">
      <Navbar />
      
      <div className="max-w-4xl mx-auto pt-24 px-4 pb-8 h-[calc(100vh-4rem)]">
        <div className="flex flex-col h-full">
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 mb-4">
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] p-4 rounded-sm ${
                    message.type === 'user'
                      ? 'bg-white/10 text-white'
                      : 'bg-white/5 text-gray-200'
                  }`}
                >
                  <ReactMarkdown 
                    className="markdown-content"
                    components={{
                      a: ({ node, ...props }) => (
                        <a 
                          {...props} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          className="text-blue-400 hover:text-blue-300 underline"
                        />
                      )
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
            {isLoading && (
              <div className="flex justify-start">
                <div className="max-w-[80%] p-4 rounded-sm bg-white/5 text-gray-200">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Thinking...</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="flex gap-4">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              className="bg-white/5 border-white/10"
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              disabled={isLoading}
            />
            <Button
              onClick={handleSend}
              className="bg-white/10 hover:bg-white/20"
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Chat;