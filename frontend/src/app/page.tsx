"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, ChevronRight, Loader2, CheckCircle, Brain, X } from "lucide-react";
import { createSession, uploadResume, ROLE_OPTIONS } from "@/lib/api";

type Step = "info" | "role" | "resume" | "processing";

export default function HomePage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("info");
  const [name, setName] = useState("");
  const [selectedRole, setSelectedRole] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [profile, setProfile] = useState<any>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped?.type === "application/pdf" || dropped?.name.endsWith(".txt")) {
      setFile(dropped);
      setError("");
    } else {
      setError("Please upload a PDF or TXT file.");
    }
  }, []);

  const handleSubmit = async () => {
    if (!file || !name || !selectedRole) return;
    setStep("processing");
    setError("");
    try {
      const session = await createSession(name, selectedRole);
      setSessionId(session.id);
      const parsed = await uploadResume(session.id, file);
      setProfile(parsed.extracted_profile);
      // Brief pause to show profile
      setTimeout(() => {
        router.push(`/interview?session=${session.id}`);
      }, 2500);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Something went wrong. Please try again.");
      setStep("resume");
    }
  };

  const steps = ["info", "role", "resume"];
  const currentIdx = steps.indexOf(step);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16 relative overflow-hidden">
      {/* Background orbs */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full bg-accent/5 blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 rounded-full bg-purple-800/5 blur-3xl" />
      </div>

      <div className="w-full max-w-xl relative z-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-10"
        >
          <div className="inline-flex items-center gap-2 mb-4 px-3 py-1.5 rounded-full border border-accent/30 bg-accent/10 text-accent text-xs font-medium tracking-wider uppercase">
            <Brain className="w-3.5 h-3.5" /> AI Screening System
          </div>
          <p className="text-text-dim text-sm">
            Dynamic interviews grounded in real ML knowledge — tailored to you.
          </p>
        </motion.div>

        {/* Progress dots */}
        {step !== "processing" && (
          <div className="flex justify-center gap-2 mb-8">
            {steps.map((s, i) => (
              <div
                key={s}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  i <= currentIdx ? "w-8 bg-accent" : "w-4 bg-border"
                }`}
              />
            ))}
          </div>
        )}

        {/* Card */}
        <motion.div
          className="bg-surface border border-border rounded-2xl p-8 glow"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <AnimatePresence mode="wait">
            {/* Step 1: Name */}
            {step === "info" && (
              <motion.div
                key="info"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <h2 className="text-xl font-semibold mb-1">Welcome, candidate</h2>
                <p className="text-text-dim text-sm mb-6">Let's start with your name.</p>
                <input
                  type="text"
                  placeholder="Full name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && name.trim().length >= 2 && setStep("role")}
                  className="w-full bg-bg border border-border rounded-xl px-4 py-3 text-text placeholder:text-muted focus:outline-none focus:border-accent/60 transition-colors font-mono text-sm"
                  autoFocus
                />
                <button
                  onClick={() => setStep("role")}
                  disabled={name.trim().length < 2}
                  className="mt-4 w-full flex items-center justify-center gap-2 bg-accent hover:bg-accent-light disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium rounded-xl px-4 py-3 transition-colors"
                >
                  Continue <ChevronRight className="w-4 h-4" />
                </button>
              </motion.div>
            )}

            {/* Step 2: Role */}
            {step === "role" && (
              <motion.div
                key="role"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <h2 className="text-xl font-semibold mb-1">Select your target role</h2>
                <p className="text-text-dim text-sm mb-6">
                  This determines which knowledge base powers your interview.
                </p>
                <div className="space-y-3">
                  {ROLE_OPTIONS.map((role) => (
                    <button
                      key={role.value}
                      onClick={() => setSelectedRole(role.value)}
                      className={`w-full text-left p-4 rounded-xl border transition-all ${
                        selectedRole === role.value
                          ? "border-accent bg-accent/10 text-text"
                          : "border-border bg-bg hover:border-muted text-text-dim hover:text-text"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <span className="text-2xl">{role.icon}</span>
                        <div>
                          <div className="font-medium text-sm">{role.label}</div>
                          <div className="text-xs text-text-dim mt-0.5">{role.description}</div>
                        </div>
                        {selectedRole === role.value && (
                          <CheckCircle className="w-4 h-4 text-accent ml-auto" />
                        )}
                      </div>
                    </button>
                  ))}
                </div>
                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => setStep("info")}
                    className="flex-1 border border-border rounded-xl px-4 py-3 text-text-dim hover:text-text transition-colors text-sm"
                  >
                    Back
                  </button>
                  <button
                    onClick={() => setStep("resume")}
                    disabled={!selectedRole}
                    className="flex-1 bg-accent hover:bg-accent-light disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium rounded-xl px-4 py-3 transition-colors flex items-center justify-center gap-2"
                  >
                    Continue <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            )}

            {/* Step 3: Resume Upload */}
            {step === "resume" && (
              <motion.div
                key="resume"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <h2 className="text-xl font-semibold mb-1">Upload your resume</h2>
                <p className="text-text-dim text-sm mb-6">
                  PDF or TXT — your background shapes the questions.
                </p>

                {/* Drop zone */}
                <div
                  onDrop={handleDrop}
                  onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                  onDragLeave={() => setIsDragging(false)}
                  onClick={() => document.getElementById("file-input")?.click()}
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                    isDragging
                      ? "border-accent bg-accent/10"
                      : file
                      ? "border-success/60 bg-success/5"
                      : "border-border hover:border-muted"
                  }`}
                >
                  <input
                    id="file-input"
                    type="file"
                    accept=".pdf,.txt"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) { setFile(f); setError(""); }
                    }}
                  />
                  {file ? (
                    <div className="flex flex-col items-center gap-2">
                      <CheckCircle className="w-8 h-8 text-success" />
                      <span className="text-sm font-medium text-text">{file.name}</span>
                      <span className="text-xs text-text-dim">{(file.size / 1024).toFixed(1)} KB</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); setFile(null); }}
                        className="text-xs text-danger flex items-center gap-1 mt-1"
                      >
                        <X className="w-3 h-3" /> Remove
                      </button>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2 text-text-dim">
                      <Upload className="w-8 h-8" />
                      <span className="text-sm">Drop your resume here or click to browse</span>
                      <span className="text-xs">PDF or TXT, max 10MB</span>
                    </div>
                  )}
                </div>

                {error && (
                  <p className="text-danger text-xs mt-3 flex items-center gap-1">
                    <X className="w-3 h-3" /> {error}
                  </p>
                )}

                <div className="flex gap-3 mt-6">
                  <button
                    onClick={() => setStep("role")}
                    className="flex-1 border border-border rounded-xl px-4 py-3 text-text-dim hover:text-text transition-colors text-sm"
                  >
                    Back
                  </button>
                  <button
                    onClick={handleSubmit}
                    disabled={!file}
                    className="flex-1 bg-accent hover:bg-accent-light disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium rounded-xl px-4 py-3 transition-colors flex items-center justify-center gap-2"
                  >
                    Start Interview <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </motion.div>
            )}

            {/* Processing */}
            {step === "processing" && (
              <motion.div
                key="processing"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center py-6"
              >
                {!profile ? (
                  <>
                    <Loader2 className="w-10 h-10 text-accent animate-spin mx-auto mb-4" />
                    <h3 className="font-semibold text-lg mb-1">Analysing your resume…</h3>
                    <p className="text-text-dim text-sm">Building your personalised interview</p>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-10 h-10 text-success mx-auto mb-4" />
                    <h3 className="font-semibold text-lg mb-1">Profile extracted!</h3>
                    <p className="text-text-dim text-sm mb-4">Generating your questions…</p>
                    <div className="flex flex-wrap gap-2 justify-center">
                      {profile.skills?.slice(0, 6).map((s: string) => (
                        <span key={s} className="px-2 py-1 bg-accent/10 text-accent text-xs rounded-lg border border-accent/20">
                          {s}
                        </span>
                      ))}
                    </div>
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        <p className="text-center text-text-dim text-xs mt-6">
          Questions are dynamically generated from authoritative ML textbooks via RAG.
        </p>
      </div>
    </div>
  );
}
