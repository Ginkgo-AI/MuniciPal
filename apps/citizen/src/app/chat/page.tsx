import { Providers } from "@/lib/providers";
import { ChatInput } from "./chat-input";
import { MessageList } from "./message-list";

export default function ChatPage() {
  return (
    <Providers>
      <div className="flex flex-col h-screen max-w-3xl mx-auto">
        <header className="border-b border-[var(--border)] p-4">
          <h1 className="text-lg font-semibold">Chat with Munici-Pal</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Ask about permits, services, and more
          </p>
        </header>
        <MessageList />
        <ChatInput />
      </div>
    </Providers>
  );
}
