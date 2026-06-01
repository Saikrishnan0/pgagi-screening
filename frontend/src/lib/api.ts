import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 60000,
});

// Types
export interface Session {
  id: string;
  candidate_name: string;
  target_role: string;
  status: string;
  total_questions: number;
  created_at: string;
  extracted_profile?: any;
}

export interface Question {
  id: string;
  session_id: string;
  sequence_number: number;
  question_text: string;
  question_type: string;
  difficulty: string;
  topic_tags: string[];
  source_books: string[];
}

export interface Summary {
  session_id: string;
  candidate_name: string;
  target_role: string;
  overall_score: number | null;
  recommendation: string | null;
  strengths: string[];
  weaknesses: string[];
  topic_scores: { topic: string; score: number; comment: string }[];
  detailed_feedback: string | null;
  total_questions: number;
  questions_answered: number;
  generated_at: string | null;
}

// API Calls
export const createSession = async (name: string, role: string): Promise<Session> => {
  const { data } = await api.post("/sessions/", { candidate_name: name, target_role: role });
  return data;
};

export const uploadResume = async (sessionId: string, file: File): Promise<any> => {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post(`/resume/upload/${sessionId}`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const startInterview = async (sessionId: string): Promise<any> => {
  const { data } = await api.post(`/interview/start/${sessionId}`);
  return data;
};

export const submitAnswer = async (questionId: string, answer: string): Promise<any> => {
  const { data } = await api.post(`/interview/answer/${questionId}`, { answer });
  return data;
};

export const completeInterview = async (sessionId: string): Promise<Summary> => {
  const { data } = await api.post(`/interview/complete/${sessionId}`);
  return data;
};

export const getSummary = async (sessionId: string): Promise<Summary> => {
  const { data } = await api.get(`/interview/summary/${sessionId}`);
  return data;
};

export const ROLE_OPTIONS = [
  {
    value: "ai_ml",
    label: "AI/ML Engineer",
    description: "Machine learning algorithms, model design, deep learning",
    icon: "🤖",
  },
  {
    value: "data_science",
    label: "Data Scientist",
    description: "Applied ML, data analysis, statistical modeling",
    icon: "📊",
  },
  {
    value: "advanced_ml",
    label: "Senior ML / Research",
    description: "Advanced theory, research-level ML, pattern recognition",
    icon: "🔬",
  },
];
