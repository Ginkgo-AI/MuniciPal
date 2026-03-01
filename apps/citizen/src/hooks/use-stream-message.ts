"use client";

import { useState, useCallback, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { API_BASE } from "@/lib/api";

interface StreamEvent {
    type: "token" | "citations" | "metadata" | "done" | "error";
    data: unknown;
}

interface StreamingState {
    isStreaming: boolean;
    content: string;
    citations: Array<Record<string, unknown>>;
    confidence: number | null;
    low_confidence: boolean | null;
}

/**
 * Hook for streaming chat responses via SSE.
 *
 * Returns a `streamMessage` function that sends a message to the
 * `/chat/stream` endpoint and progressively updates the streaming state
 * as tokens arrive.
 *
 * Once complete, it invalidates the session query so the polling picks
 * up the persisted message.
 */
export function useStreamMessage() {
    const queryClient = useQueryClient();
    const abortRef = useRef<AbortController | null>(null);

    const [streaming, setStreaming] = useState<StreamingState>({
        isStreaming: false,
        content: "",
        citations: [],
        confidence: null,
        low_confidence: null,
    });

    const streamMessage = useCallback(
        async ({
            sessionId,
            message,
        }: {
            sessionId: string;
            message: string;
        }) => {
            // Abort any previous stream
            abortRef.current?.abort();
            const controller = new AbortController();
            abortRef.current = controller;

            // Reset streaming state
            setStreaming({
                isStreaming: true,
                content: "",
                citations: [],
                confidence: null,
                low_confidence: null,
            });

            try {
                const response = await fetch(`${API_BASE}/chat/stream`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ session_id: sessionId, message }),
                    signal: controller.signal,
                });

                if (!response.ok) {
                    throw new Error(`Stream failed: ${response.status}`);
                }

                const reader = response.body!.getReader();
                const decoder = new TextDecoder();
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split("\n");
                    buffer = lines.pop() || "";

                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed.startsWith("data: ")) continue;

                        try {
                            const event: StreamEvent = JSON.parse(trimmed.substring(6));

                            switch (event.type) {
                                case "token":
                                    setStreaming((prev) => ({
                                        ...prev,
                                        content: prev.content + (event.data as string),
                                    }));
                                    break;
                                case "citations":
                                    setStreaming((prev) => ({
                                        ...prev,
                                        citations: event.data as Array<Record<string, unknown>>,
                                    }));
                                    break;
                                case "metadata": {
                                    const meta = event.data as {
                                        confidence: number;
                                        low_confidence: boolean;
                                    };
                                    setStreaming((prev) => ({
                                        ...prev,
                                        confidence: meta.confidence,
                                        low_confidence: meta.low_confidence,
                                    }));
                                    break;
                                }
                                case "done":
                                    setStreaming((prev) => ({ ...prev, isStreaming: false }));
                                    // Invalidate session so polling picks up the persisted message
                                    queryClient.invalidateQueries({
                                        queryKey: ["session", sessionId],
                                    });
                                    return;
                                case "error":
                                    setStreaming((prev) => ({
                                        ...prev,
                                        isStreaming: false,
                                        content:
                                            prev.content +
                                            "\n\nSorry, an error occurred. Please try again.",
                                    }));
                                    return;
                            }
                        } catch {
                            // Skip malformed JSON lines
                        }
                    }
                }

                // Stream ended without "done" event
                setStreaming((prev) => ({ ...prev, isStreaming: false }));
                queryClient.invalidateQueries({
                    queryKey: ["session", sessionId],
                });
            } catch (err) {
                if ((err as Error).name === "AbortError") return;
                setStreaming((prev) => ({
                    ...prev,
                    isStreaming: false,
                    content:
                        prev.content || "Sorry, something went wrong. Please try again.",
                }));
            }
        },
        [queryClient]
    );

    const resetStreaming = useCallback(() => {
        setStreaming({
            isStreaming: false,
            content: "",
            citations: [],
            confidence: null,
            low_confidence: null,
        });
    }, []);

    return {
        streaming,
        streamMessage,
        resetStreaming,
    };
}
