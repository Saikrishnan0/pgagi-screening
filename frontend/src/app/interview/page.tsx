"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Loader2, BookOpen, Clock, AlertCircle,
  Send, Brain, Zap
} from "lucide-react";
import { startInterview, submitAnswer, completeInterview, Question } from "@/lib/api";

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: "text-success border-success/30 bg-success/10",
  medium: "text-warning border-warning/30 bg-warning/10",
  hard: "text-danger border-danger/30 bg-danger/10",
};

const TYPE_ICONS: Record<string, string> = {
  conceptual: "🧠",
  applied: "⚙️",
  behavioral: "💬",
  followup: "🔍",
};

function InterviewContent() {
  const router = useRouter();
  const params = useSearchParams();
  const sessionId = params.get("session") || "";

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [answer, setAnswer] = useState("");
  const [answeredCount, setAnsweredCount] = useState(0);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isFollowUp, setIsFollowUp] = useState(false);
  const [followUpMessage, setFollowUpMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const timerRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (!sessionId) { router.push("/"); return; }
    initInterview();
    timerRef.current = setInterval(() => setElapsedTime(t => t + 1), 1000);
    return () => clearInterval(timerRef.current);
  }, []);

  const initInterview = async () => {
    try {
      const data = await startInterview(sessionId);
      setCurrentQuestion(data.first_question);
      setTotalQuestions(data.total_questions);
      setLoading(false);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to start interview.");
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!answer.trim() || !currentQuestion || submitting) return;
    setSubmitting(true);
    setIsFollowUp(false);
    setFollowUpMessage("");
    try {
      const result = await submitAnswer(currentQuestion.id, answer.trim());
      setAnsweredCount(prev => prev + 1);
      setAnswer("");

      if (result.is_complete) {
        try { await completeInterview(sessionId); } catch (e) {}
        router.push(`/results?session=${sessionId}`);
      } else {
        // Check if this is a follow-up question
        if (result.next_question?.question_type === "followup") {
          setIsFollowUp(true);
          setFollowUpMessage(result.message);
          setTotalQuestions(prev => prev + 1);
        }
        setCurrentQuestion(result.next_question);
        textareaRef.current?.focus();
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to submit answer.");
    } finally {
      setSubmitting(false);
    }
  };

  const formatTime = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  const progress = totalQuestions > 0 ? (answeredCount / totalQuestions) * 100 : 0;

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <Loader2 className="w-10 h-10 text-accent animate-spin" />
        <p className="text-text-dim">Generating your personalised questions via RAG…</p>
        <p className="text-xs text-muted">This may take 10–20 seconds</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-10 h-10 text-danger" />
        <p className="text-text-dim">{error}</p>
        <button onClick={() => router.push("/")} className="text-accent text-sm underline">
          Start over
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top bar */}
      <div className="border-b border-border bg-surface/80 backdrop-blur-md sticky top-0 z-20">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <Brain className="w-4 h-4 text-accent" />
            <span className="font-medium text-text">PGAGI Interview</span>
          </div>

          <div className="flex-1 mx-8">
            <div className="flex justify-between text-xs text-text-dim mb-1">
              <span>{answeredCount} answered</span>
              <span>{totalQuestions} total</span>
            </div>
            <div className="h-1.5 bg-border rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-accent to-accent-light rounded-full"
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>

          <div className="flex items-center gap-1.5 text-text-dim text-xs font-mono">
            <Clock className="w-3.5 h-3.5" />
            {formatTime(elapsedTime)}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 max-w-3xl mx-auto w-full px-4 py-10">
        <AnimatePresence mode="wait">
          {currentQuestion && (
            <motion.div
              key={currentQuestion.id}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4 }}
            >
              {/* Follow-up banner */}
              <AnimatePresence>
                {isFollowUp && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="mb-4 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-accent/10 border border-accent/30 text-accent text-sm"
                  >
                    <Zap className="w-4 h-4 flex-shrink-0" />
                    <span><strong>Follow-up:</strong> Your answer was detailed — here's a deeper question based on what you said.</span>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Question metadata */}
              <div className="flex flex-wrap items-center gap-2 mb-5">
                <span className="text-xs text-text-dim font-mono">
                  Q{currentQuestion.sequence_number} of {totalQuestions}
                </span>
                <span className={`px-2 py-0.5 rounded-full text-xs border font-medium ${DIFFICULTY_COLORS[currentQuestion.difficulty] || DIFFICULTY_COLORS.medium}`}>
                  {currentQuestion.difficulty}
                </span>
                <span className="text-xs text-text-dim">
                  {TYPE_ICONS[currentQuestion.question_type] || "💬"} {currentQuestion.question_type}
                </span>
                {currentQuestion.topic_tags?.slice(0, 3).map(tag => (
                  <span key={tag} className="px-2 py-0.5 rounded-full text-xs bg-accent/10 text-accent border border-accent/20">
                    {tag}
                  </span>
                ))}
              </div>

              {/* Question card */}
              <div className={`border rounded-2xl p-6 mb-6 glow ${isFollowUp ? "bg-accent/5 border-accent/30" : "bg-surface border-border"}`}>
                <p className="text-text text-lg leading-relaxed font-medium">
                  {currentQuestion.question_text}
                </p>

                {currentQuestion.source_books?.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-border flex items-start gap-2 text-xs text-text-dim">
                    <BookOpen className="w-3.5 h-3.5 mt-0.5 text-muted flex-shrink-0" />
                    <span>Sources: {currentQuestion.source_books.join(" · ")}</span>
                  </div>
                )}
              </div>

              {/* Answer box */}
              <div className="bg-surface border border-border rounded-2xl overflow-hidden">
                <div className="px-4 pt-3 pb-1 border-b border-border flex items-center gap-2">
                  <span className="text-xs text-text-dim">Your answer</span>
                  <span className="text-xs text-muted ml-auto">Ctrl+Enter to submit</span>
                </div>
                <textarea
                  ref={textareaRef}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && e.ctrlKey) handleSubmit(); }}
                  placeholder="Type your answer here…"
                  className="w-full bg-transparent px-4 py-4 text-text text-sm resize-none focus:outline-none placeholder:text-muted min-h-[180px]"
                  autoFocus
                />
                <div className="px-4 pb-4 flex items-center justify-between">
                  <span className="text-xs text-muted font-mono">{answer.length} chars</span>
                  <button
                    onClick={handleSubmit}
                    disabled={!answer.trim() || submitting}
                    className="flex items-center gap-2 bg-accent hover:bg-accent-light disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-xl px-5 py-2.5 transition-colors"
                  >
                    {submitting ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
                    ) : (
                      <><Send className="w-4 h-4" /> Submit Answer</>
                    )}
                  </button>
                </div>
              </div>

              <p className="text-center text-xs text-muted mt-4">
                {answeredCount >= 2
                  ? "💡 Detailed answers may trigger follow-up questions"
                  : "Take your time — there's no time limit per question."}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function InterviewPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center"><Loader2 className="w-8 h-8 text-accent animate-spin" /></div>}>
      <InterviewContent />
    </Suspense>
  );
}
