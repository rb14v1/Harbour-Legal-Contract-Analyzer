import { type FormEvent, useEffect, useState } from "react";
import { api } from "../api/client";
import type { ContractQuery, Paginated } from "../types";

export function QueryHistoryPage() {
  const [queries, setQueries] = useState<ContractQuery[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    const response = await api.get<Paginated<ContractQuery>>("/queries/");
    setQueries(response.data.results);
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAsk(event: FormEvent) {
    event.preventDefault();
    setAsking(true);
    setError("");
    try {
      await api.post("/queries/", { question_text: question, contract_id: null });
      setQuestion("");
      await load();
    } catch {
      setError("Could not get an answer.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="page">
      <h2>Query History</h2>
      <p className="hint">Ask a question across all processed contracts, or review past questions and answers.</p>

      <form onSubmit={handleAsk} className="form-row">
        <input
          placeholder="e.g. Summarize payment terms across our vendor contracts"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          required
        />
        <button type="submit" disabled={asking}>
          {asking ? "Asking..." : "Ask across all contracts"}
        </button>
      </form>
      {error && <div className="error-banner">{error}</div>}

      <ul className="query-list">
        {queries.map((query) => (
          <li key={query.id} className="query-item">
            <div className="query-question">
              <strong>{query.question_text}</strong>
              <span className="query-meta">
                {query.asked_by_email} &middot; {query.contract ? `contract #${query.contract}` : "all contracts"} &middot;{" "}
                {new Date(query.created_at).toLocaleString()}
              </span>
            </div>
            <div className="query-answer">{query.answer_text}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
