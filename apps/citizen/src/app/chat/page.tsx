"use client";

import { useState, useCallback } from "react";
import { Providers } from "@/lib/providers";
import { useLoadedModels } from "@/hooks/use-models";
import { ChatHeader } from "./chat-header";
import { ChatInput } from "./chat-input";
import { MessageList } from "./message-list";
import { ChatSidebar } from "./chat-sidebar";
import { ModelSettings } from "./model-settings";

function ChatLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [modelSettingsOpen, setModelSettingsOpen] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const { data: loadedData } = useLoadedModels();

  const currentModel = loadedData?.models?.[0]?.name ?? undefined;

  const handleNewChat = useCallback(() => {
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
    <div className="flex h-screen overflow-hidden">
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

      <div className="flex flex-col flex-1 min-w-0">
        <ChatHeader
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          onOpenModelSettings={() => setModelSettingsOpen(true)}
          currentModel={currentModel}
        />
        <MessageList />
        <ChatInput />
      </div>

      <ModelSettings
        isOpen={modelSettingsOpen}
        onClose={() => setModelSettingsOpen(false)}
      />
    </div>
  );
}

export default function ChatPage() {
  return (
    <Providers>
      <ChatLayout />
    </Providers>
  );
}
