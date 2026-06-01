"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  Loader2, CheckCircle, XCircle, TrendingUp,
  TrendingDown, Star, BookOpen, RotateCcw, Award
} from "lucide-react";
import { getSummary, Summary, ROLE_OPTIONS } from "@/lib/api";

const RECOMMENDATION_STYLES: Record<string, { color: string; icon: any; bg: string }> = {
  "Strong Hire": { color: "text-success", icon: Award, bg: "bg-success/10 border-success/30" },
  Hire: { color: "text-accent", icon: CheckCircle, bg: "bg-accent/10 border-accent/30" },
  Maybe: { color: "text-warning", icon: TrendingUp, bg: "bg-warning/10 border-warning/30" },
  "No Hire": { color: "text-danger", icon: XCircle, bg: "bg-danger/10 border-danger/30" },
};

function ScoreRing({ score }: { score: number }) {
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 75 ? "#22C55E" : score >= 50 ? "#F59E0B" : "#EF4444";

  return (
    <div className="relative w-36 h-36 mx-auto">
      <svg className="w-full h-full -rotate-90" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r={radius} fill="none" stroke="#1E1E2E" strokeWidth="10" />
        <motion.circle
          cx="64" cy="64" r={radius}
          fill="none" stroke={color} strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="text-3xl font-bold text-text"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          {score}
        </motion.span>
        <span className="text-xs text-text-dim">/ 100</span>
      </div>
    </div>
  );
}

function ResultsContent() {
  const router = useRouter();
  const params = useSearchParams();
  const sessionId = params.get("session") || "";
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId) { router.push("/"); return; }
    loadSummary();
  }, []);

  const loadSummary = async () => {
    try {
      const data = await getSummary(sessionId);
      setSummary(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load results.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <Loader2 className="w-10 h-10 text-accent animate-spin" />
        <p className="text-text-dim">Generating your evaluation…</p>
      </div>
    );
  }

  if (error || !summary) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-danger">{error || "No results found."}</p>
        <button onClick={() => router.push("/")} className="text-accent underline text-sm">
          Start over
        </button>
      </div>
    );
  }

  const recStyle = RECOMMENDATION_STYLES[summary.recommendation || ""] || RECOMMENDATION_STYLES["Maybe"];
  const RecIcon = recStyle.icon;
  const roleLabel = ROLE_OPTIONS.find(r => r.value === summary.target_role)?.label || summary.target_role;

  return (
    <div className="min-h-screen py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <motion.div className="text-center mb-10" initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold text-text mb-1">Interview Complete</h1>
          <p className="text-text-dim text-sm">{summary.candidate_name} · {roleLabel}</p>
        </motion.div>

        {/* Score + Recommendation */}
        <motion.div
          className="bg-surface border border-border rounded-2xl p-8 mb-6 glow text-center"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
        >
          {summary.overall_score != null ? (
            <ScoreRing score={summary.overall_score} />
          ) : (
            <p className="text-text-dim text-sm">Score not available</p>
          )}

          {summary.recommendation && (
            <div className={`inline-flex items-center gap-2 mt-5 px-4 py-2 rounded-full border text-sm font-medium ${recStyle.bg} ${recStyle.color}`}>
              <RecIcon className="w-4 h-4" />
              {summary.recommendation}
            </div>
          )}

          <p className="text-xs text-muted mt-3 font-mono">
            {summary.questions_answered} / {summary.total_questions} questions answered
          </p>
        </motion.div>

        {/* Topic Scores */}
        {summary.topic_scores && summary.topic_scores.length > 0 && (
          <motion.div
            className="bg-surface border border-border rounded-2xl p-6 mb-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <Star className="w-4 h-4 text-accent" /> Topic Breakdown
            </h3>
            <div className="space-y-4">
              {summary.topic_scores.map((ts, i) => (
                <div key={i}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-text-dim">{ts.topic}</span>
                    <span className="font-mono text-text">{ts.score}/100</span>
                  </div>
                  <div className="h-2 bg-border rounded-full overflow-hidden">
                    <motion.div
                      className="h-full rounded-full"
                      style={{
                        background: ts.score >= 75 ? "#22C55E" : ts.score >= 50 ? "#F59E0B" : "#EF4444",
                      }}
                      initial={{ width: 0 }}
                      animate={{ width: `${ts.score}%` }}
                      transition={{ duration: 1, delay: 0.3 + i * 0.1 }}
                    />
                  </div>
                  <p className="text-xs text-muted mt-1">{ts.comment}</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Strengths & Weaknesses */}
        <motion.div
          className="grid grid-cols-2 gap-4 mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="bg-surface border border-border rounded-2xl p-5">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 text-success">
              <TrendingUp className="w-4 h-4" /> Strengths
            </h3>
            {summary.strengths?.length ? (
              <ul className="space-y-2">
                {summary.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-text-dim">
                    <CheckCircle className="w-3 h-3 text-success mt-0.5 flex-shrink-0" />
                    {s}
                  </li>
                ))}
              </ul>
            ) : <p className="text-xs text-muted">None identified.</p>}
          </div>

          <div className="bg-surface border border-border rounded-2xl p-5">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 text-warning">
              <TrendingDown className="w-4 h-4" /> Areas to Improve
            </h3>
            {summary.weaknesses?.length ? (
              <ul className="space-y-2">
                {summary.weaknesses.map((w, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-text-dim">
                    <XCircle className="w-3 h-3 text-warning mt-0.5 flex-shrink-0" />
                    {w}
                  </li>
                ))}
              </ul>
            ) : <p className="text-xs text-muted">None identified.</p>}
          </div>
        </motion.div>

        {/* Detailed Feedback */}
        {summary.detailed_feedback && (
          <motion.div
            className="bg-surface border border-border rounded-2xl p-6 mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <h3 className="font-semibold text-sm mb-4 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-accent" /> Detailed Feedback
            </h3>
            <p className="text-text-dim text-sm leading-relaxed whitespace-pre-wrap">
              {summary.detailed_feedback}
            </p>
          </motion.div>
        )}

        {/* CTA */}
        <motion.div
          className="text-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
        >
          <button
            onClick={() => router.push("/")}
            className="inline-flex items-center gap-2 bg-accent hover:bg-accent-light text-white font-medium rounded-xl px-6 py-3 transition-colors"
          >
            <RotateCcw className="w-4 h-4" /> Start a New Interview
          </button>
        </motion.div>
      </div>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><Loader2 className="w-8 h-8 text-accent animate-spin" /></div>}>
      <ResultsContent />
    </Suspense>
  );
}
