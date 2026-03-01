"use client";

import { useState, useCallback } from "react";
import { Providers } from "@/lib/providers";
import { ChatHeader } from "./chat-header";
import { ChatInput } from "./chat-input";
import { MessageList } from "./message-list";
import { ChatSidebar } from "./chat-sidebar";
import { ModelSettings } from "./model-settings";

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [modelSettingsOpen, setModelSettingsOpen] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const handleNewChat = useCallback(() => {
    // Clear session — will create a new one on next message
    setActiveSessionId(null);
    window.dispatchEvent(new CustomEvent("municipal:new-chat"));
  }, []);

  const handleSelectSession = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId);
    window.dispatchEvent(
      new CustomEvent("municipal:session", { detail: sessionId })
    );
    setSidebarOpen(false);
  }, []);

  return (
    <Providers>
      <div className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <ChatSidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onNewChat={handleNewChat}
          onOpenModelSettings={() => {
            setModelSettingsOpen(true);
            setSidebarOpen(false);
          }}
        />

        {/* Main Chat Area */}
        <div className="flex flex-col flex-1 min-w-0">
          <ChatHeader
            onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
            onOpenModelSettings={() => setModelSettingsOpen(true)}
          />
          <MessageList />
          <ChatInput />
        </div>

        {/* Model Settings Panel */}
        <ModelSettings
          isOpen={modelSettingsOpen}
          onClose={() => setModelSettingsOpen(false)}
        />
      </div>
    </Providers>
  );
}
