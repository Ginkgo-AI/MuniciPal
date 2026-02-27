import { Providers } from "@/lib/providers";
import { ChatHeader } from "./chat-header";
import { ChatInput } from "./chat-input";
import { MessageList } from "./message-list";

export default function ChatPage() {
  return (
    <Providers>
      <div className="flex flex-col h-screen max-w-3xl mx-auto">
        <ChatHeader />
        <MessageList />
        <ChatInput />
      </div>
    </Providers>
  );
}
