import React, { useState } from "react";
import {
  ChevronRightIcon,
  ChevronDownIcon,
  PlusIcon,
} from "@heroicons/react/24/outline";

interface SidebarProps {
  onNavigate: (page: "agent" | "create-new") => void;
}

const Sidebar: React.FC<SidebarProps> = ({ onNavigate }) => {
  const [expandedItems, setExpandedItems] = useState<{
    [key: string]: boolean;
  }>({
    agents: true,
  });

  const toggleExpanded = (key: string) => {
    setExpandedItems((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="w-64 h-screen bg-black text-gray-300 flex flex-col border-r border-gray-900">
      {/* Logo placeholder */}
      <div className="h-16 flex items-center px-6">
        {/* Empty space for logo */}
      </div>

      {/* Main menu */}
      <div className="flex-1 overflow-y-auto py-2">
        <div className="px-2">
          {/* Agents */}
          <div
            className="flex items-center px-3 py-1.5 rounded-md hover:bg-neutral-800 cursor-pointer transition-colors"
            onClick={() => toggleExpanded("agents")}
          >
            <svg
              className="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
              />
            </svg>
            <span className="text-sm font-normal flex-1">Agents</span>
            {expandedItems.agents ? (
              <ChevronDownIcon className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRightIcon className="w-4 h-4 text-gray-500" />
            )}
          </div>

          {/* Agents submenu */}
          {expandedItems.agents && (
            <div className="ml-8 mt-0.5">
              <div
                className="flex items-center px-3 py-1.5 rounded-md hover:bg-neutral-800 cursor-pointer transition-colors"
                onClick={() => onNavigate("create-new")}
              >
                <PlusIcon className="w-4 h-4 mr-2" />
                <span className="text-sm font-normal">Create New</span>
              </div>
              <div className="flex items-center px-3 py-1.5 rounded-md hover:bg-neutral-800 cursor-pointer transition-colors">
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                  />
                </svg>
                <span className="text-sm font-normal">My Agents</span>
              </div>
              <div className="flex items-center px-3 py-1.5 rounded-md hover:bg-neutral-800 cursor-pointer transition-colors">
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
                <span className="text-sm font-normal">Actions</span>
              </div>
              <div className="flex items-center px-3 py-1.5 rounded-md hover:bg-neutral-800 cursor-pointer transition-colors">
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
                <span className="text-sm font-normal">Conversations</span>
              </div>
              <div className="flex items-center px-3 py-1.5 rounded-md hover:bg-neutral-800 cursor-pointer transition-colors">
                <svg
                  className="w-4 h-4 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                  />
                </svg>
                <span className="text-sm font-normal">Templates</span>
              </div>
            </div>
          )}

          {/* Playground */}
          <div className="flex items-center px-3 py-1.5 rounded-md hover:bg-neutral-800 cursor-pointer transition-colors">
            <svg
              className="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-sm font-normal">Playground</span>
          </div>
        </div>
      </div>

      {/* Bottom section */}
      <div className="p-4 space-y-4">
        {/* Plan info */}
        <div className="bg-neutral-900 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-500 mb-1">Free Plan</div>
          <div className="text-sm font-medium mb-2">3 minutes remaining</div>
          <button className="w-full bg-neutral-800 hover:bg-neutral-700 text-white py-1.5 px-3 rounded-md text-xs font-medium transition-colors">
            Upgrade Your Plan
          </button>
        </div>

        {/* Support and social */}
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center space-x-1">
            <button className="p-2 rounded-md hover:bg-neutral-800 transition-colors">
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
            </button>
            <span className="text-sm">Support</span>
          </div>
          <div className="flex items-center space-x-2">
            <button className="p-1.5 rounded-md hover:bg-neutral-800 transition-colors">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z" />
              </svg>
            </button>
            <button className="p-1.5 rounded-md hover:bg-neutral-800 transition-colors">
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Profile */}
        <div className="flex items-center space-x-3 px-2 py-2 rounded-md hover:bg-neutral-800 cursor-pointer transition-colors">
          <div className="w-8 h-8 rounded-full bg-neutral-700 flex items-center justify-center text-sm font-medium">
            V
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium">Victor C</div>
            <div className="text-xs text-gray-500 truncate">
              victor.f.chapman@gmail.c...
            </div>
          </div>
          <ChevronRightIcon className="w-4 h-4 text-gray-500" />
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
