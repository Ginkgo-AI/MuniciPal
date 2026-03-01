"use client";

import { useState, useEffect } from "react";
import {
    useAvailableModels,
    useLoadedModels,
    useLoadModel,
    useUnloadModel,
    useUpdateModelConfig,
    useSystemResources,
    useRecommendedModels,
} from "@/hooks/use-models";
import {
    X,
    Cpu,
    HardDrive,
    Activity,
    Zap,
    Check,
    Loader2,
    Circle,
    ChevronDown,
    MemoryStick,
    Shield,
} from "lucide-react";

interface ModelSettingsProps {
    isOpen: boolean;
    onClose: () => void;
}

const CONTEXT_PRESETS = [
    { label: "2K", value: 2048 },
    { label: "4K", value: 4096 },
    { label: "8K", value: 8192 },
    { label: "16K", value: 16384 },
    { label: "32K", value: 32768 },
    { label: "64K", value: 65536 },
    { label: "128K", value: 131072 },
];

const KEEP_ALIVE_OPTIONS = [
    { label: "5 minutes", value: "5m" },
    { label: "30 minutes", value: "30m" },
    { label: "1 hour", value: "1h" },
    { label: "4 hours", value: "4h" },
    { label: "Forever", value: "-1" },
    { label: "Unload immediately", value: "0" },
];

export function ModelSettings({ isOpen, onClose }: ModelSettingsProps) {
    const { data: availableData } = useAvailableModels();
    const { data: loadedData } = useLoadedModels();
    const { data: resources } = useSystemResources();
    const { data: recommendedData } = useRecommendedModels();
    const loadModel = useLoadModel();
    const unloadModel = useUnloadModel();
    const updateConfig = useUpdateModelConfig();

    const [selectedModel, setSelectedModel] = useState<string>("");
    const [contextLength, setContextLength] = useState(4096);
    const [keepAlive, setKeepAlive] = useState("5m");
    const [showModelDropdown, setShowModelDropdown] = useState(false);

    const available = availableData?.models ?? [];
    const loaded = loadedData?.models ?? [];
    const recommendations = recommendedData?.recommendations ?? [];

    // Set default from first available model
    useEffect(() => {
        if (available.length > 0 && !selectedModel) {
            setSelectedModel(available[0].name);
        }
    }, [available, selectedModel]);

    const isModelLoaded = (name: string) =>
        loaded.some((m) => m.name === name || m.name.startsWith(name.split(":")[0]));

    const handleLoadModel = async () => {
        if (!selectedModel) return;
        await loadModel.mutateAsync({
            model: selectedModel,
            keepAlive,
            numCtx: contextLength,
        });
    };

    const handleUnloadModel = async (name: string) => {
        await unloadModel.mutateAsync(name);
    };

    const handleApplyConfig = async () => {
        await updateConfig.mutateAsync({
            model: selectedModel || undefined,
            context_length: contextLength,
            keep_alive: keepAlive,
        });
    };

    const getFitColor = (fit: string) => {
        switch (fit) {
            case "good":
                return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
            case "moderate":
                return "text-amber-400 bg-amber-500/10 border-amber-500/20";
            case "poor":
                return "text-red-400 bg-red-500/10 border-red-500/20";
            default:
                return "text-[var(--muted-foreground)] bg-[var(--accent)]/50 border-[var(--border)]";
        }
    };

    if (!isOpen) return null;

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50"
                onClick={onClose}
            />

            {/* Panel */}
            <div className="fixed right-0 top-0 z-50 h-full w-full max-w-[420px] bg-[var(--background)] border-l border-[var(--border)] shadow-2xl overflow-y-auto animate-in slide-in-from-right duration-300">
                {/* Header */}
                <div className="sticky top-0 bg-[var(--background)]/80 backdrop-blur-md border-b border-[var(--border)] p-4 flex items-center justify-between z-10">
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-sm">
                            <Cpu className="w-4 h-4 text-white" />
                        </div>
                        <h2 className="text-base font-semibold">Model Settings</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--muted-foreground)] hover:bg-[var(--accent)] transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="p-4 space-y-5">
                    {/* Model Selector */}
                    <section>
                        <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-2 block">
                            Active Model
                        </label>
                        <div className="relative">
                            <button
                                onClick={() => setShowModelDropdown(!showModelDropdown)}
                                className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--card)] text-sm hover:border-[var(--primary)]/30 transition-colors"
                            >
                                <div className="flex items-center gap-2">
                                    {isModelLoaded(selectedModel) ? (
                                        <Circle className="w-2.5 h-2.5 fill-emerald-400 text-emerald-400" />
                                    ) : (
                                        <Circle className="w-2.5 h-2.5 text-[var(--muted-foreground)]/40" />
                                    )}
                                    <span className="font-medium truncate">
                                        {selectedModel || "Select a model…"}
                                    </span>
                                </div>
                                <ChevronDown
                                    className={`w-4 h-4 text-[var(--muted-foreground)] transition-transform ${showModelDropdown ? "rotate-180" : ""}`}
                                />
                            </button>

                            {showModelDropdown && (
                                <div className="absolute top-full left-0 right-0 mt-1 bg-[var(--card)] border border-[var(--border)] rounded-xl shadow-lg z-10 max-h-56 overflow-y-auto animate-in fade-in zoom-in-95 duration-150">
                                    {available.map((model) => (
                                        <button
                                            key={model.name}
                                            onClick={() => {
                                                setSelectedModel(model.name);
                                                setShowModelDropdown(false);
                                            }}
                                            className="w-full flex items-center gap-3 px-3 py-2.5 text-sm hover:bg-[var(--accent)] transition-colors text-left"
                                        >
                                            {isModelLoaded(model.name) ? (
                                                <Circle className="w-2 h-2 fill-emerald-400 text-emerald-400 shrink-0" />
                                            ) : (
                                                <Circle className="w-2 h-2 text-[var(--muted-foreground)]/30 shrink-0" />
                                            )}
                                            <div className="flex-1 min-w-0">
                                                <p className="font-medium truncate">{model.name}</p>
                                                <p className="text-[10px] text-[var(--muted-foreground)]">
                                                    {model.size_gb} GB · {model.parameter_size || model.family}
                                                    {model.quantization ? ` · ${model.quantization}` : ""}
                                                </p>
                                            </div>
                                            {selectedModel === model.name && (
                                                <Check className="w-4 h-4 text-[var(--primary)] shrink-0" />
                                            )}
                                        </button>
                                    ))}
                                    {available.length === 0 && (
                                        <p className="px-3 py-4 text-xs text-center text-[var(--muted-foreground)]">
                                            No models found. Is Ollama running?
                                        </p>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Load / Unload */}
                        <div className="flex gap-2 mt-2">
                            <button
                                onClick={handleLoadModel}
                                disabled={!selectedModel || loadModel.isPending}
                                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 hover:bg-emerald-500/20 disabled:opacity-40 transition-all"
                            >
                                {loadModel.isPending ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                    <Zap className="w-3.5 h-3.5" />
                                )}
                                Load
                            </button>
                            <button
                                onClick={() => selectedModel && handleUnloadModel(selectedModel)}
                                disabled={!selectedModel || !isModelLoaded(selectedModel) || unloadModel.isPending}
                                className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 disabled:opacity-40 transition-all"
                            >
                                {unloadModel.isPending ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                ) : (
                                    <X className="w-3.5 h-3.5" />
                                )}
                                Unload
                            </button>
                        </div>
                    </section>

                    {/* Currently Loaded */}
                    {loaded.length > 0 && (
                        <section>
                            <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-2 block">
                                Loaded in Memory ({loaded.length})
                            </label>
                            <div className="space-y-1.5">
                                {loaded.map((m) => (
                                    <div
                                        key={m.name}
                                        className="flex items-center justify-between px-3 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] text-sm"
                                    >
                                        <div className="flex items-center gap-2 min-w-0">
                                            <Circle className="w-2 h-2 fill-emerald-400 text-emerald-400 shrink-0" />
                                            <span className="font-medium truncate">{m.name}</span>
                                        </div>
                                        <div className="text-[10px] text-[var(--muted-foreground)] shrink-0 ml-2">
                                            {m.size_gb} GB · ctx {m.context_length}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Context Length */}
                    <section>
                        <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-2 block">
                            Context Length
                        </label>
                        <div className="flex flex-wrap gap-1.5">
                            {CONTEXT_PRESETS.map((preset) => (
                                <button
                                    key={preset.value}
                                    onClick={() => setContextLength(preset.value)}
                                    className={`
                    px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-150
                    ${contextLength === preset.value
                                            ? "bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)] shadow-sm"
                                            : "bg-[var(--card)] text-[var(--foreground)] border-[var(--border)] hover:border-[var(--primary)]/30"
                                        }
                  `}
                                >
                                    {preset.label}
                                </button>
                            ))}
                        </div>
                        <p className="text-[10px] text-[var(--muted-foreground)] mt-1.5">
                            Larger context = more memory. Current: {contextLength.toLocaleString()} tokens
                        </p>
                    </section>

                    {/* Keep Alive */}
                    <section>
                        <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-2 block">
                            Keep Loaded
                        </label>
                        <div className="grid grid-cols-2 gap-1.5">
                            {KEEP_ALIVE_OPTIONS.map((option) => (
                                <button
                                    key={option.value}
                                    onClick={() => setKeepAlive(option.value)}
                                    className={`
                    px-3 py-2 rounded-lg text-xs font-medium border transition-all duration-150 text-left
                    ${keepAlive === option.value
                                            ? "bg-[var(--primary)] text-[var(--primary-foreground)] border-[var(--primary)] shadow-sm"
                                            : "bg-[var(--card)] text-[var(--foreground)] border-[var(--border)] hover:border-[var(--primary)]/30"
                                        }
                  `}
                                >
                                    {option.label}
                                </button>
                            ))}
                        </div>
                    </section>

                    {/* Apply Button */}
                    <button
                        onClick={handleApplyConfig}
                        disabled={updateConfig.isPending}
                        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
              bg-[var(--primary)] text-[var(--primary-foreground)]
              hover:opacity-90 active:scale-[0.98]
              disabled:opacity-50 transition-all text-sm font-medium shadow-sm"
                    >
                        {updateConfig.isPending ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Check className="w-4 h-4" />
                        )}
                        Apply Configuration
                    </button>

                    {/* System Resources */}
                    {resources && (
                        <section>
                            <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-2 block">
                                System Resources
                            </label>
                            <div className="grid grid-cols-2 gap-2">
                                <div className="px-3 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)]">
                                    <div className="flex items-center gap-1.5 mb-1">
                                        <MemoryStick className="w-3.5 h-3.5 text-blue-400" />
                                        <p className="text-[10px] font-medium text-[var(--muted-foreground)]">
                                            RAM
                                        </p>
                                    </div>
                                    <p className="text-sm font-semibold">
                                        {resources.available_ram_gb} GB{" "}
                                        <span className="text-[10px] font-normal text-[var(--muted-foreground)]">
                                            / {resources.total_ram_gb} GB
                                        </span>
                                    </p>
                                    <div className="w-full h-1.5 bg-[var(--accent)] rounded-full mt-1.5 overflow-hidden">
                                        <div
                                            className="h-full bg-blue-500 rounded-full transition-all duration-500"
                                            style={{ width: `${resources.ram_usage_percent}%` }}
                                        />
                                    </div>
                                </div>

                                <div className="px-3 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)]">
                                    <div className="flex items-center gap-1.5 mb-1">
                                        <Cpu className="w-3.5 h-3.5 text-violet-400" />
                                        <p className="text-[10px] font-medium text-[var(--muted-foreground)]">
                                            CPU
                                        </p>
                                    </div>
                                    <p className="text-sm font-semibold">
                                        {resources.cpu_count}{" "}
                                        <span className="text-[10px] font-normal text-[var(--muted-foreground)]">
                                            cores
                                        </span>
                                    </p>
                                </div>

                                {resources.gpu_available && (
                                    <div className="col-span-2 px-3 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)]">
                                        <div className="flex items-center gap-1.5 mb-1">
                                            <Activity className="w-3.5 h-3.5 text-emerald-400" />
                                            <p className="text-[10px] font-medium text-[var(--muted-foreground)]">
                                                GPU
                                            </p>
                                        </div>
                                        <p className="text-sm font-semibold">{resources.gpu_name}</p>
                                    </div>
                                )}

                                <div className="col-span-2 px-3 py-2.5 rounded-xl bg-[var(--card)] border border-[var(--border)]">
                                    <div className="flex items-center gap-1.5">
                                        <HardDrive className="w-3.5 h-3.5 text-[var(--muted-foreground)]" />
                                        <p className="text-[10px] text-[var(--muted-foreground)]">
                                            {resources.platform}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </section>
                    )}

                    {/* Model Recommendations */}
                    {recommendations.length > 0 && (
                        <section>
                            <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-2 block">
                                Recommended Models
                            </label>
                            <div className="space-y-1.5">
                                {recommendations.map((rec) => (
                                    <button
                                        key={rec.model.name}
                                        onClick={() => setSelectedModel(rec.model.name)}
                                        className={`
                      w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border text-left transition-all
                      ${selectedModel === rec.model.name
                                                ? "border-[var(--primary)]/30 bg-[var(--primary)]/5"
                                                : "border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)]/20"
                                            }
                    `}
                                    >
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <p className="text-sm font-medium truncate">
                                                    {rec.model.name}
                                                </p>
                                                <span
                                                    className={`inline-flex items-center px-1.5 py-0.5 rounded-md text-[9px] font-semibold border ${getFitColor(rec.fit)}`}
                                                >
                                                    {rec.fit === "good" && <Shield className="w-2.5 h-2.5 mr-0.5" />}
                                                    {rec.fit.toUpperCase()}
                                                </span>
                                            </div>
                                            <p className="text-[10px] text-[var(--muted-foreground)] mt-0.5 truncate">
                                                {rec.reason}
                                            </p>
                                        </div>
                                        <div className="text-[10px] text-[var(--muted-foreground)] shrink-0">
                                            {rec.model.size_gb} GB
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </section>
                    )}
                </div>
            </div>
        </>
    );
}
