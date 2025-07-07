import React from "react";
import { ChevronRightIcon, PlusIcon } from "@heroicons/react/24/outline";

interface SidebarProps {
  onNavigate: (page: "agent" | "create-new") => void;
  currentPage: "agent" | "create-new";
}

const Sidebar: React.FC<SidebarProps> = ({ onNavigate, currentPage }) => {
  const getLinkClassName = (page: "agent" | "create-new") => {
    return `flex items-center px-4 py-2 rounded-md cursor-pointer transition-colors ${
      currentPage === page
        ? "bg-neutral-800 text-white"
        : "text-gray-300 hover:bg-neutral-800 hover:text-white"
    }`;
  };

  return (
    <div className="w-64 h-screen bg-black text-gray-300 flex flex-col border-r border-neutral-800">
      {/* Logo placeholder */}
      <div className="h-16 flex items-center px-6">
        {/* Empty space for logo */}
      </div>

      {/* Main menu */}
      <div className="flex-1 overflow-y-auto py-2">
        <div className="px-1 space-y-0.5">
          {/* Create New */}
          <div
            className={getLinkClassName("create-new")}
            onClick={() => onNavigate("create-new")}
          >
            <PlusIcon className="w-5 h-5 mr-[0.45rem]" />
            <span className="text-sm font-normal">Create New</span>
          </div>

          {/* My Agents */}
          <div
            className={getLinkClassName("agent")}
            onClick={() => onNavigate("agent")}
          >
            <svg
              className="w-5 h-5 mr-[0.45rem]"
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

          {/* Actions */}
          <div className="flex items-center px-4 py-2 rounded-md hover:bg-neutral-800 cursor-pointer transition-colors">
            <svg
              className="w-5 h-5 mr-[0.45rem]"
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

          {/* Conversations */}
          <div className="flex items-center px-4 py-2 rounded-md hover:bg-neutral-800 cursor-pointer transition-colors">
            <svg
              className="w-5 h-5 mr-[0.45rem]"
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

          {/* Templates */}
          <div className="flex items-center px-4 py-2 rounded-md hover:bg-neutral-800 cursor-pointer transition-colors">
            <svg
              className="w-5 h-5 mr-[0.45rem]"
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
      </div>

      {/* Profile section */}
      <div className="p-4">
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
