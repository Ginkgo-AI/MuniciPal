"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

// --- Types ---

interface ModelInfo {
    name: string;
    size_bytes: number;
    size_gb: number;
    parameter_size: string;
    family: string;
    quantization: string;
    format: string;
    modified_at: string;
    digest: string;
    model_type: "text" | "vision" | "embedding" | "code";
    is_chat_capable: boolean;
}

interface LoadedModelInfo {
    name: string;
    size_bytes: number;
    size_gb: number;
    size_vram: number;
    vram_gb: number;
    context_length: number;
    expires_at: string;
}

interface SystemResources {
    total_ram_bytes: number;
    total_ram_gb: number;
    available_ram_bytes: number;
    available_ram_gb: number;
    ram_usage_percent: number;
    cpu_count: number;
    platform: string;
    gpu_available: boolean;
    gpu_name: string;
}

interface ModelRecommendation {
    model: ModelInfo;
    fit: "good" | "moderate" | "poor" | "unknown";
    reason: string;
    score: number;
}

// --- Hooks ---

export function useAvailableModels() {
    return useQuery<{ models: ModelInfo[] }>({
        queryKey: ["models", "available"],
        queryFn: () => apiFetch("/models/available"),
        staleTime: 60_000,
    });
}

export function useLoadedModels() {
    return useQuery<{ models: LoadedModelInfo[] }>({
        queryKey: ["models", "loaded"],
        queryFn: () => apiFetch("/models/loaded"),
        refetchInterval: 10_000,
    });
}

export function useSystemResources() {
    return useQuery<SystemResources>({
        queryKey: ["system", "resources"],
        queryFn: () => apiFetch("/system/resources"),
        staleTime: 30_000,
    });
}

export function useRecommendedModels() {
    return useQuery<{
        recommendations: ModelRecommendation[];
        system: SystemResources;
    }>({
        queryKey: ["models", "recommended"],
        queryFn: () => apiFetch("/models/recommended"),
        staleTime: 60_000,
    });
}

export function useLoadModel() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: ({
            model,
            keepAlive = "-1",
            numCtx,
        }: {
            model: string;
            keepAlive?: string;
            numCtx?: number;
        }) =>
            apiFetch("/models/load", {
                method: "POST",
                body: JSON.stringify({
                    model,
                    keep_alive: keepAlive,
                    num_ctx: numCtx,
                }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["models", "loaded"] });
        },
    });
}

export function useUnloadModel() {
    const queryClient = useQueryClient();
    return useMutation({
        mutationFn: (model: string) =>
            apiFetch("/models/unload", {
                method: "POST",
                body: JSON.stringify({ model }),
            }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["models", "loaded"] });
        },
    });
}

export function useUpdateModelConfig() {
    return useMutation({
        mutationFn: (config: {
            model?: string;
            context_length?: number;
            keep_alive?: string;
        }) =>
            apiFetch("/models/config", {
                method: "PATCH",
                body: JSON.stringify(config),
            }),
    });
}

export type {
    ModelInfo,
    LoadedModelInfo,
    SystemResources,
    ModelRecommendation,
};
