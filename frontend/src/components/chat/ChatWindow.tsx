"use client";

import type { AgentName } from "@/lib/types";
import { useChat } from "@/hooks/useChat";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";
import { AgentIndicator } from "./AgentIndicator";

export function ChatWindow() {
  const {
    messages,
    isStreaming,
    currentAgent,
    sendMessage,
    uploadFile,
    rateFeedback,
    cancelStream,
  } = useChat();

  return (
    <div className="flex h-full flex-col">
      {/* Message list (scrollable) */}
      <MessageList
        messages={messages}
        onRate={rateFeedback}
        onSendSuggestion={sendMessage}
      />


      {/* Agent streaming indicator */}
      <AgentIndicator
        agent={currentAgent as AgentName | null}
        isStreaming={isStreaming}
      />

      {/* Input bar */}
      <ChatInput
        onSend={sendMessage}
        onFileUpload={uploadFile}
        isStreaming={isStreaming}
        onCancel={cancelStream}
      />
    </div>
  );
}
