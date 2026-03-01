"use client";

import { useState, useRef, useEffect } from "react";
import {
    useSessionList,
    useCreateSession,
    useRenameSession,
    useDeleteSession,
} from "@/hooks/use-chat";
import {
    Plus,
    MessageSquare,
    MoreHorizontal,
    Pencil,
    Trash2,
    X,
    Check,
    PanelLeftClose,
    Cpu,
} from "lucide-react";

interface ChatSidebarProps {
    isOpen: boolean;
    onClose: () => void;
    activeSessionId: string | null;
    onSelectSession: (sessionId: string) => void;
    onNewChat: () => void;
    onOpenModelSettings: () => void;
}

export function ChatSidebar({
    isOpen,
    onClose,
    activeSessionId,
    onSelectSession,
    onNewChat,
    onOpenModelSettings,
}: ChatSidebarProps) {
    const { data: sessions } = useSessionList();
    const createSession = useCreateSession();
    const renameSession = useRenameSession();
    const deleteSession = useDeleteSession();

    const [editingId, setEditingId] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState("");
    const [menuOpenId, setMenuOpenId] = useState<string | null>(null);
    const editInputRef = useRef<HTMLInputElement>(null);
    const menuRef = useRef<HTMLDivElement>(null);

    // Focus input when editing starts
    useEffect(() => {
        if (editingId) {
            editInputRef.current?.focus();
            editInputRef.current?.select();
        }
    }, [editingId]);

    // Close menu on outside click
    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setMenuOpenId(null);
            }
        }
        if (menuOpenId) {
            document.addEventListener("mousedown", handleClick);
            return () => document.removeEventListener("mousedown", handleClick);
        }
    }, [menuOpenId]);

    const handleNewChat = async () => {
        onNewChat();
    };

    const handleRename = (sessionId: string, currentTitle: string | null) => {
        setEditingId(sessionId);
        setEditTitle(currentTitle || "");
        setMenuOpenId(null);
    };

    const handleSaveRename = async (sessionId: string) => {
        if (editTitle.trim()) {
            await renameSession.mutateAsync({
                sessionId,
                title: editTitle.trim(),
            });
        }
        setEditingId(null);
    };

    const handleDelete = async (sessionId: string) => {
        setMenuOpenId(null);
        await deleteSession.mutateAsync(sessionId);
        if (activeSessionId === sessionId) {
            onNewChat();
        }
    };

    const formatTime = (dateStr: string) => {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMin = Math.floor(diffMs / 60_000);
        const diffHr = Math.floor(diffMs / 3_600_000);
        const diffDay = Math.floor(diffMs / 86_400_000);

        if (diffMin < 1) return "Just now";
        if (diffMin < 60) return `${diffMin}m ago`;
        if (diffHr < 24) return `${diffHr}h ago`;
        if (diffDay < 7) return `${diffDay}d ago`;
        return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    };

    return (
        <>
            {/* Backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40 lg:hidden"
                    onClick={onClose}
                />
            )}

            {/* Sidebar */}
            <aside
                className={`
          fixed top-0 left-0 z-50 h-full w-[280px]
          bg-[var(--background)] border-r border-[var(--border)]
          flex flex-col
          transition-transform duration-300 ease-in-out
          ${isOpen ? "translate-x-0" : "-translate-x-full"}
          lg:relative lg:z-auto
          shadow-xl lg:shadow-none
        `}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-3 border-b border-[var(--border)]">
                    <h2 className="text-sm font-semibold text-[var(--foreground)] tracking-tight">
                        Conversations
                    </h2>
                    <button
                        onClick={onClose}
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)] transition-colors"
                    >
                        <PanelLeftClose className="w-4 h-4" />
                    </button>
                </div>

                {/* New Chat Button */}
                <div className="p-3">
                    <button
                        onClick={handleNewChat}
                        className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl
              bg-[var(--primary)] text-[var(--primary-foreground)]
              hover:opacity-90 active:scale-[0.98]
              transition-all duration-200 text-sm font-medium shadow-sm"
                    >
                        <Plus className="w-4 h-4" />
                        New Chat
                    </button>
                </div>

                {/* Session List */}
                <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
                    {sessions && sessions.length > 0 ? (
                        sessions.map((session) => {
                            const isActive = session.session_id === activeSessionId;
                            const isEditing = editingId === session.session_id;
                            const displayTitle =
                                session.title || `Chat ${session.session_id.slice(0, 6)}…`;

                            return (
                                <div
                                    key={session.session_id}
                                    className={`
                    group relative flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer
                    transition-all duration-150
                    ${isActive
                                            ? "bg-[var(--accent)] text-[var(--foreground)] shadow-sm"
                                            : "text-[var(--muted-foreground)] hover:bg-[var(--accent)]/50 hover:text-[var(--foreground)]"
                                        }
                  `}
                                    onClick={() => {
                                        if (!isEditing) {
                                            onSelectSession(session.session_id);
                                        }
                                    }}
                                >
                                    <MessageSquare className="w-4 h-4 shrink-0 opacity-60" />

                                    {isEditing ? (
                                        <form
                                            className="flex-1 flex items-center gap-1"
                                            onSubmit={(e) => {
                                                e.preventDefault();
                                                handleSaveRename(session.session_id);
                                            }}
                                        >
                                            <input
                                                ref={editInputRef}
                                                value={editTitle}
                                                onChange={(e) => setEditTitle(e.target.value)}
                                                className="flex-1 text-sm bg-transparent border-b border-[var(--primary)] outline-none py-0.5"
                                                onKeyDown={(e) => {
                                                    if (e.key === "Escape") setEditingId(null);
                                                }}
                                            />
                                            <button
                                                type="submit"
                                                className="w-6 h-6 flex items-center justify-center rounded-md hover:bg-[var(--accent)] text-green-500"
                                            >
                                                <Check className="w-3.5 h-3.5" />
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => setEditingId(null)}
                                                className="w-6 h-6 flex items-center justify-center rounded-md hover:bg-[var(--accent)] text-[var(--muted-foreground)]"
                                            >
                                                <X className="w-3.5 h-3.5" />
                                            </button>
                                        </form>
                                    ) : (
                                        <>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium truncate">
                                                    {displayTitle}
                                                </p>
                                                <p className="text-[10px] opacity-60 mt-0.5">
                                                    {session.message_count} messages ·{" "}
                                                    {formatTime(session.last_active)}
                                                </p>
                                            </div>

                                            {/* Actions menu */}
                                            <div className="relative" ref={menuOpenId === session.session_id ? menuRef : null}>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation();
                                                        setMenuOpenId(
                                                            menuOpenId === session.session_id
                                                                ? null
                                                                : session.session_id
                                                        );
                                                    }}
                                                    className={`
                            w-7 h-7 rounded-lg flex items-center justify-center
                            transition-opacity duration-150
                            hover:bg-[var(--accent)]
                            ${isActive || menuOpenId === session.session_id ? "opacity-100" : "opacity-0 group-hover:opacity-100"}
                          `}
                                                >
                                                    <MoreHorizontal className="w-4 h-4" />
                                                </button>

                                                {menuOpenId === session.session_id && (
                                                    <div className="absolute right-0 top-8 z-50 w-36 py-1 bg-[var(--card)] border border-[var(--border)] rounded-xl shadow-lg animate-in fade-in zoom-in-95 duration-150">
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleRename(session.session_id, session.title);
                                                            }}
                                                            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--accent)] transition-colors"
                                                        >
                                                            <Pencil className="w-3.5 h-3.5" /> Rename
                                                        </button>
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleDelete(session.session_id);
                                                            }}
                                                            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-500 hover:bg-red-500/10 transition-colors"
                                                        >
                                                            <Trash2 className="w-3.5 h-3.5" /> Delete
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        </>
                                    )}
                                </div>
                            );
                        })
                    ) : (
                        <div className="px-3 py-8 text-center">
                            <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-20" />
                            <p className="text-xs text-[var(--muted-foreground)]">
                                No conversations yet
                            </p>
                        </div>
                    )}
                </div>

                {/* Footer — Model Settings */}
                <div className="border-t border-[var(--border)] p-3">
                    <button
                        onClick={onOpenModelSettings}
                        className="w-full flex items-center gap-2 px-3 py-2 rounded-xl
              text-sm text-[var(--muted-foreground)]
              hover:bg-[var(--accent)] hover:text-[var(--foreground)]
              transition-all duration-150"
                    >
                        <Cpu className="w-4 h-4" />
                        Model Settings
                    </button>
                </div>
            </aside>
        </>
    );
}
