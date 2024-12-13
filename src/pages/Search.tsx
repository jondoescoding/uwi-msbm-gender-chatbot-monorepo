import { useState, useEffect } from "react";
import axios from "axios";
import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import ArticleCard from "@/components/ArticleCard";
import { 
  Trash2, 
  Edit, 
  BookmarkPlus, 
  CalendarIcon, 
  Check, 
  X 
} from "lucide-react";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import Footer from "@/components/Footer";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { format } from "date-fns";
import { cn } from "@/lib/utils";
import { MultiSelect } from "@/components/ui/multi-select";

// Add the topics data
const topics = [
  "Gender Discrimination & Bias",
  "Gender Inequality",
  "Gender Based Violence",
  "Gender Stereotypes & Roles",
  "Gender Identity & Expression",
  "Gender Sexuality",
  "Gender Health",
  "Gender Education",
  "Gender at Work",
  "Gender in Media",
  "Gender Equality",
  "Gender Activism",
  "Gender Sensitivity",
  "Gender Analysis"
];

interface Dashboard {
  _id: string;
  dashboard_name: string;
  selected_keywords: string[];
  selected_countries: string[];
  start_date?: string;
  end_date?: string;
  created_at: string;
}

const Search = (): JSX.Element => {
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);
  const [country, setCountry] = useState("");
  const [countries, setCountries] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startDate, setStartDate] = useState<Date>(new Date(2024, 0, 1));
  const [endDate, setEndDate] = useState<Date>(new Date(2024, 11, 31));
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalArticles, setTotalArticles] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const [savedDashboards, setSavedDashboards] = useState<Dashboard[]>([]);
  const [isDashboardsLoading, setIsDashboardsLoading] = useState(true);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [editingDashboardId, setEditingDashboardId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");

  // Add state for category search
  const [categorySearch, setCategorySearch] = useState("");

  // Filter topics based on search
  const filteredTopics = topics.filter(topic => 
    topic.toLowerCase().includes(categorySearch.toLowerCase())
  );

  // Configure axios base URL and instance
  const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL,
    timeout: 120000,  // Increase to 120 seconds
    headers: {
      'Content-Type': 'application/json'
    },
    withCredentials: true
  });

  // Add request interceptor for debugging and retry logic
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

  // Add response interceptor for debugging and retry logic
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
      const originalRequest = error.config;

      // If the error is a timeout and we haven't retried yet
      if (error.code === 'ECONNABORTED' && !originalRequest._retry) {
        originalRequest._retry = true;
        console.log('Request timed out, retrying...');
        
        // Show user-friendly message
        setError('Request is taking longer than usual. Retrying...');
        
        try {
          return await api(originalRequest);
        } catch (retryError) {
          console.error('Retry failed:', retryError);
          setError('The request is still taking too long. Please try again or contact support if the issue persists.');
          return Promise.reject(retryError);
        }
      }

      console.error('🔴 [Frontend] API Error:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        config: {
          url: error.config?.url,
          method: error.config?.method,
          baseURL: error.config?.baseURL,
          headers: error.config?.headers
        },
        origin: window.location.origin
      });

      // Handle specific error cases
      if (error.response?.status === 404) {
        setError('The requested resource was not found. Please try again later.');
      } else if (error.code === 'ERR_NETWORK') {
        setError('Network error: Unable to connect to the server. Please check your connection and try again.');
      } else if (error.response?.status === 403) {
        setError('Access denied. Please check your permissions and try again.');
      } else if (error.code === 'ECONNABORTED') {
        setError('The request took too long to complete. We will automatically retry. If the problem persists, please try again later.');
      } else {
        setError(error.response?.data?.detail || error.message || 'An unexpected error occurred');
      }

      return Promise.reject(error);
    }
  );

  useEffect(() => {
    const fetchCountries = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const response = await api.get('/keyword-search/countries');
        const data = response.data;
        
        if (data.countries && Array.isArray(data.countries)) {
          setCountries(data.countries);
        } else {
          throw new Error("Invalid data format received");
        }
      } catch (error) {
        console.error('Error fetching countries:', error);
        setError(error instanceof Error ? error.message : 'Failed to fetch countries');
      } finally {
        setIsLoading(false);
      }
    };

    fetchCountries();
  }, []);

  // Fetch saved dashboards
  useEffect(() => {
    const fetchDashboards = async () => {
      try {
        setIsDashboardsLoading(true);
        setDashboardError(null);
        
        const response = await api.get('/keyword-search/dashboards');
        const data = response.data;
        setSavedDashboards(data.dashboards);
      } catch (error) {
        console.error('Error fetching dashboards:', error);
        setDashboardError(error instanceof Error ? error.message : 'Failed to fetch dashboards');
      } finally {
        setIsDashboardsLoading(false);
      }
    };

    fetchDashboards();
  }, []);

  const handleSearch = async () => {
    try {
      setIsSearching(true);
      setError(null);
      
      // Construct the params object
      const params: any = {
        page: currentPage,
        page_size: 10,
        category: selectedCategories,  // Always include categories array
        country: selectedCountries,    // Always include countries array
        start_date: startDate?.toISOString(),
        end_date: endDate?.toISOString()
      };

      // Log the search parameters
      console.log('Search parameters:', {
        selectedCategories,
        selectedCountries,
        startDate: startDate?.toISOString(),
        endDate: endDate?.toISOString()
      });
      
      console.log('Sending request with params:', params);
      const response = await api.get('/keyword-search/search', { params });
      console.log('Received response:', response.data);
      
      const data = response.data;
      setSearchResults(data.articles);
      setTotalPages(data.total_pages);
      setTotalArticles(data.total);
      
    } catch (error) {
      console.error('Error searching articles:', error);
      setError(error instanceof Error ? error.message : 'Failed to search articles');
    } finally {
      setIsSearching(false);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
      handleSearch();
    }
  };

  // Add pagination helper function
  const getPageNumbers = (current: number, total: number): number[] => {
    const delta = 2; // This will show 2 numbers on each side
    const range: number[] = [];
    const rangeWithDots: number[] = [];
    let l: number;

    for (let i = 1; i <= total; i++) {
      if (i === 1 || i === total || (i >= current - delta && i <= current + delta)) {
        range.push(i);
      }
    }

    for (let i = 0; i < range.length; i++) {
      if (l) {
        if (range[i] - l === 2) {
          rangeWithDots.push(l + 1);
        } else if (range[i] - l !== 1) {
          rangeWithDots.push(-1); // -1 represents dots
        }
      }
      rangeWithDots.push(range[i]);
      l = range[i];
    }

    return rangeWithDots;
  };

  const handleSaveQuery = async () => {
    try {
      if (!selectedCategories.length || !selectedCountries.length) {
        alert("Please select at least one category and one country before saving");
        return;
      }

      const dashboardData = {
        selected_keywords: selectedCategories,
        selected_countries: selectedCountries,
        start_date: startDate?.toISOString(),
        end_date: endDate?.toISOString()
      };

      const response = await api.post('/keyword-search/dashboards', dashboardData);
      setSavedDashboards([...savedDashboards, response.data.dashboard]);
    } catch (error) {
      console.error('Error saving dashboard:', error);
      alert('Failed to save dashboard');
    }
  };

  const loadDashboard = async (dashboard: Dashboard) => {
    try {
      // Set the form values from the dashboard
      setSelectedCategories(dashboard.selected_keywords || []);
      setSelectedCountries(dashboard.selected_countries || []);
      
      if (dashboard.start_date) {
        setStartDate(new Date(dashboard.start_date));
      }
      if (dashboard.end_date) {
        setEndDate(new Date(dashboard.end_date));
      }

      // Construct search parameters with the dashboard values
      const params: any = {
        page: 1,  // Reset to first page
        page_size: 10,
        category: dashboard.selected_keywords || [],
        country: dashboard.selected_countries || [],
        start_date: dashboard.start_date,
        end_date: dashboard.end_date
      };

      // Make the API call with the dashboard values
      setIsSearching(true);
      const response = await api.get('/keyword-search/search', { params });
      const data = response.data;
      
      // Update results
      setSearchResults(data.articles);
      setTotalPages(data.total_pages);
      setTotalArticles(data.total);
      setCurrentPage(1);  // Reset to first page
      
    } catch (error) {
      console.error('Error loading dashboard:', error);
      setError(error instanceof Error ? error.message : 'Failed to load dashboard');
    } finally {
      setIsSearching(false);
    }
  };

  const handleEditClick = (e: React.MouseEvent, dashboard: Dashboard) => {
    e.stopPropagation(); // Prevent triggering the dashboard load
    setEditingDashboardId(dashboard._id);
    setEditingName(dashboard.dashboard_name);
  };

  const handleEditCancel = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering the dashboard load
    setEditingDashboardId(null);
    setEditingName("");
  };

  const handleEditSave = async (e: React.MouseEvent, dashboardId: string) => {
    e.stopPropagation();
    try {
      const response = await api.patch(`/keyword-search/dashboards/${dashboardId}`, {
        dashboard_name: editingName
      });

      setSavedDashboards(savedDashboards.map(dashboard => 
        dashboard._id === dashboardId ? response.data.dashboard : dashboard
      ));
      
      setEditingDashboardId(null);
      setEditingName("");
    } catch (error) {
      console.error('Error updating dashboard:', error);
      alert('Failed to update dashboard name');
    }
  };

  const handleCategorySelect = (values: string[]) => {
    // Log the selection change
    console.log('Updating categories:', values);
    setSelectedCategories(values);
  };

  const handleCountrySelect = (values: string[]) => {
    // Log the selection change
    console.log('Updating countries:', values);
    setSelectedCountries(values);
  };

  const handleClearSearch = () => {
    // Reset all search parameters
    setSelectedCategories([]);
    setSelectedCountries([]);
    setStartDate(new Date(2024, 0, 1));
    setEndDate(new Date(2024, 11, 31));
    setSearchResults([]);
    setTotalPages(1);
    setTotalArticles(0);
    setCurrentPage(1);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-black">
      <Navbar />
      
      <div className="flex flex-col md:flex-row min-h-[calc(100vh-4rem)] pt-16">
        {/* Sidebar - Full width on mobile, normal on desktop */}
        <div className="w-full md:w-64 border-b md:border-b-0 md:border-r border-white/10 p-6 space-y-6">
          <h2 className="text-lg text-white font-light">Saved Queries</h2>
          <div className="space-y-2">
            {isDashboardsLoading ? (
              <div className="text-sm text-gray-400">Loading saved queries...</div>
            ) : dashboardError ? (
              <div className="text-sm text-red-400">{dashboardError}</div>
            ) : savedDashboards.length === 0 ? (
              <div className="text-sm text-gray-400">No saved queries found</div>
            ) : (
              savedDashboards.map((dashboard) => (
                <Card 
                  key={dashboard._id} 
                  className="p-3 bg-black/40 backdrop-blur-xl border border-white/10 transition-all duration-300 hover:border-white/30 hover:bg-white/5 cursor-pointer"
                  onClick={() => loadDashboard(dashboard)}
                >
                  <div className="flex items-center justify-between">
                    {editingDashboardId === dashboard._id ? (
                      <div className="flex-1 flex items-center space-x-2" onClick={e => e.stopPropagation()}>
                        <Input
                          value={editingName}
                          onChange={(e) => setEditingName(e.target.value)}
                          className="flex-1 h-7 text-sm bg-black/60"
                          autoFocus
                        />
                        <button 
                          className="text-green-400 hover:text-green-300 transition-colors"
                          onClick={(e) => handleEditSave(e, dashboard._id)}
                        >
                          <Check className="h-4 w-4" />
                        </button>
                        <button 
                          className="text-red-400 hover:text-red-300 transition-colors"
                          onClick={handleEditCancel}
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    ) : (
                      <>
                        <span className="text-sm text-gray-300">{dashboard.dashboard_name}</span>
                        <div className="flex space-x-2">
                          <button 
                            className="text-gray-400 hover:text-white transition-colors"
                            onClick={(e) => handleEditClick(e, dashboard)}
                          >
                            <Edit className="h-4 w-4" />
                          </button>
                          <button className="text-gray-400 hover:text-red-400 transition-colors">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </Card>
              ))
            )}
          </div>
        </div>

        {/* Main content - Full width on mobile */}
        <div className="flex-1 p-4 md:p-8">
          <div className="max-w-4xl mx-auto space-y-8">
            {/* Filters - Stack on mobile */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 md:p-6 bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg">
              <div className="space-y-2">
                <label className="text-sm text-gray-400">Select Categories</label>
                <MultiSelect
                  options={topics}
                  selected={selectedCategories}
                  onChange={handleCategorySelect}
                  placeholder="Choose research topics"
                />
                
                {/* Selected Categories Display */}
                <div className="flex flex-wrap gap-2 mt-2">
                  {selectedCategories.map((category) => (
                    <div
                      key={category}
                      className="bg-white/10 text-sm px-2 py-1 rounded-md flex items-center gap-1"
                    >
                      <span>{category}</span>
                      <button
                        onClick={() => setSelectedCategories(prev => prev.filter(c => c !== category))}
                        className="hover:text-red-400"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm text-gray-400">Select Countries</label>
                <MultiSelect
                  options={countries}
                  selected={selectedCountries}
                  onChange={handleCountrySelect}
                  placeholder={isLoading ? "Loading countries..." : "Choose countries"}
                  disabled={isLoading}
                />
                
                {/* Selected Countries Display */}
                <div className="flex flex-wrap gap-2 mt-2">
                  {selectedCountries.map((country) => (
                    <div
                      key={country}
                      className="bg-white/10 text-sm px-2 py-1 rounded-md flex items-center gap-1"
                    >
                      <span>{country}</span>
                      <button
                        onClick={() => setSelectedCountries(prev => prev.filter(c => c !== country))}
                        className="hover:text-red-400"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
                {error && <p className="text-sm text-red-500">{error}</p>}
              </div>

              <div className="space-y-2">
                <label className="text-sm text-gray-400">Start Date</label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-start text-left font-normal bg-black/60 border-input hover:bg-black/80",
                        !startDate && "text-muted-foreground"
                      )}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {startDate ? format(startDate, "PPP") : <span>Pick a date</span>}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0 bg-black border-white/10">
                    <Calendar
                      mode="single"
                      selected={startDate}
                      onSelect={setStartDate}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>

              <div className="space-y-2">
                <label className="text-sm text-gray-400">End Date</label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-start text-left font-normal bg-black/60 border-input hover:bg-black/80",
                        !endDate && "text-muted-foreground"
                      )}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {endDate ? format(endDate, "PPP") : <span>Pick a date</span>}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0 bg-black border-white/10">
                    <Calendar
                      mode="single"
                      selected={endDate}
                      onSelect={setEndDate}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>

              <div className="col-span-1 md:col-span-2 flex gap-4">
                <Button 
                  className="bg-blue-600 hover:bg-blue-700 text-white flex-1 transition-all duration-300 hover:scale-105"
                  onClick={handleSearch}
                  disabled={isSearching}
                >
                  {isSearching ? "Searching..." : "Search Articles"}
                </Button>

                <Button 
                  variant="outline" 
                  className="border-white/10 hover:bg-white/5 text-white flex-1 transition-all duration-300 hover:scale-105"
                  onClick={handleSaveQuery}
                >
                  <BookmarkPlus className="mr-2 h-4 w-4" />
                  Save Search Query
                </Button>

                <Button 
                  variant="outline" 
                  className="border-red-500/30 hover:bg-red-500/10 text-red-500 flex-1 transition-all duration-300 hover:scale-105"
                  onClick={handleClearSearch}
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Clear Search
                </Button>
              </div>
            </div>

            {/* Search Results - Adjust padding for mobile */}
            <div className="space-y-4 md:space-y-6">
              <h2 className="text-2xl font-light text-white">
                {isSearching ? "Searching..." : totalArticles > 0 ? `Found ${totalArticles} Total Articles` : "No Articles Found"}
              </h2>
              {error && (
                <div className="p-4 bg-red-500/10 border border-red-500 rounded-lg">
                  <p className="text-red-500">{error}</p>
                </div>
              )}
              <div className="space-y-4">
                {searchResults.map((article, index) => (
                  <ArticleCard key={index} {...article} />
                ))}
              </div>
            </div>

            {totalPages > 1 && (
              <div className="flex justify-center mt-4 md:mt-6 mb-4 md:mb-8">
                <Pagination>
                  <PaginationContent>
                    <PaginationItem>
                      <PaginationPrevious
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          if (currentPage > 1) handlePageChange(currentPage - 1);
                        }}
                        className={currentPage === 1 ? "pointer-events-none opacity-50" : ""}
                      />
                    </PaginationItem>

                    {getPageNumbers(currentPage, totalPages).map((pageNum, idx) => (
                      <PaginationItem key={idx}>
                        {pageNum === -1 ? (
                          <span className="px-4 text-gray-400">...</span>
                        ) : (
                          <PaginationLink
                            href="#"
                            onClick={(e) => {
                              e.preventDefault();
                              handlePageChange(pageNum);
                            }}
                            isActive={currentPage === pageNum}
                          >
                            {pageNum}
                          </PaginationLink>
                        )}
                      </PaginationItem>
                    ))}

                    <PaginationItem>
                      <PaginationNext
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          if (currentPage < totalPages) handlePageChange(currentPage + 1);
                        }}
                        className={currentPage === totalPages ? "pointer-events-none opacity-50" : ""}
                      />
                    </PaginationItem>
                  </PaginationContent>
                </Pagination>
              </div>
            )}
          </div>
        </div>
      </div>
      <Footer />
    </div>
  );
};

export default Search;
