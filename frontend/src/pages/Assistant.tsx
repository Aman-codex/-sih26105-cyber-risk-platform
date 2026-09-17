import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Bot, Send, User } from "lucide-react";
import { apiClient } from "@/api/client";

interface AssistantAnswer {
  intent: string;
  answer: string;
  supporting_data: Record<string, unknown>;
}

const SUGGESTIONS = [
  "What is our highest financial risk?",
  "What are the main risk drivers?",
  "Which control should we invest in?",
  "What are our compliance gaps?",
  "How has our risk changed over time?",
];

interface Turn {
  question: string;
  answer: string;
}

export default function Assistant() {
  const [history, setHistory] = useState<Turn[]>([]);
  const [input, setInput] = useState("");

  const askMutation = useMutation({
    mutationFn: (question: string) => apiClient.post<AssistantAnswer>("/assistant/ask", { question }).then((r) => r.data),
    onSuccess: (data, question) => setHistory((h) => [...h, { question, answer: data.answer }]),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    askMutation.mutate(input.trim());
    setInput("");
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">AI Decision Support</h2>
        <p className="text-sm text-muted-foreground">
          Ask about risk, compliance, or investments. Answers are pulled directly from the platform's own calculations — never invented.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => askMutation.mutate(s)}
            className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground hover:bg-muted/30"
          >
            {s}
          </button>
        ))}
      </div>

      <div className="space-y-4 rounded-lg border border-border bg-muted/10 p-4 min-h-[200px]">
        {history.length === 0 && !askMutation.isPending && (
          <p className="text-sm text-muted-foreground">Ask a question above or click a suggestion to get started.</p>
        )}
        {history.map((turn, i) => (
          <div key={i} className="space-y-2">
            <div className="flex items-start gap-2">
              <User size={16} className="mt-0.5 text-muted-foreground" />
              <p className="text-sm font-medium">{turn.question}</p>
            </div>
            <div className="flex items-start gap-2">
              <Bot size={16} className="mt-0.5 text-primary" />
              <p className="text-sm text-muted-foreground">{turn.answer}</p>
            </div>
          </div>
        ))}
        {askMutation.isPending && (
          <div className="flex items-center gap-2">
            <Bot size={16} className="text-primary" />
            <p className="text-sm text-muted-foreground">Thinking...</p>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm"
        />
        <button type="submit" className="flex items-center gap-1 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground">
          <Send size={14} />
        </button>
      </form>
    </div>
  );
}
