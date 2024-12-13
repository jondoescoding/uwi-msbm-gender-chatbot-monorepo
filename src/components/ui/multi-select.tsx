import React, { useState } from 'react';
import { X } from 'lucide-react';

interface MultiSelectProps {
  options: string[];
  selected: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function MultiSelect({
  options,
  selected,
  onChange,
  placeholder = "Select options...",
  disabled = false
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');

  const filteredOptions = options.filter(option => 
    option.toLowerCase().includes(search.toLowerCase())
  );

  const handleSelect = (option: string) => {
    if (selected.includes(option)) {
      onChange(selected.filter(item => item !== option));
    } else {
      onChange([...selected, option]);
    }
  };

  const handleRemove = (option: string) => {
    onChange(selected.filter(item => item !== option));
  };

  return (
    <div className="relative">
      {/* Selected items display */}
      <div 
        className="min-h-[40px] p-2 border border-white/10 rounded-md bg-black/60 cursor-pointer"
        onClick={() => !disabled && setIsOpen(!isOpen)}
      >
        <div className="flex flex-wrap gap-2">
          {selected.length === 0 ? (
            <span className="text-gray-400">{placeholder}</span>
          ) : (
            selected.map(item => (
              <span 
                key={item}
                className="bg-white/10 text-sm px-2 py-1 rounded-md flex items-center gap-1"
              >
                {item}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemove(item);
                  }}
                  className="hover:text-red-400"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))
          )}
        </div>
      </div>

      {/* Dropdown */}
      {isOpen && !disabled && (
        <div className="absolute z-50 w-full mt-1 bg-black border border-white/10 rounded-md shadow-lg">
          {/* Search input */}
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full p-2 bg-transparent border-b border-white/10 focus:outline-none"
            placeholder="Search..."
            onClick={(e) => e.stopPropagation()}
          />

          {/* Options list */}
          <div className="max-h-60 overflow-auto">
            {filteredOptions.length === 0 ? (
              <div className="p-2 text-gray-400">No options found</div>
            ) : (
              filteredOptions.map(option => (
                <div
                  key={option}
                  className={`
                    p-2 cursor-pointer flex items-center gap-2 hover:bg-white/5
                    ${selected.includes(option) ? 'bg-white/10' : ''}
                  `}
                  onClick={() => handleSelect(option)}
                >
                  <div className={`
                    w-4 h-4 border rounded-sm flex items-center justify-center
                    ${selected.includes(option) ? 'bg-blue-600 border-blue-600' : 'border-white/20'}
                  `}>
                    {selected.includes(option) && (
                      <svg 
                        viewBox="0 0 24 24" 
                        className="w-3 h-3 text-white"
                        fill="none" 
                        stroke="currentColor" 
                        strokeWidth="2"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    )}
                  </div>
                  <span>{option}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
} 