import { type FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { Contract, ContractClause, ContractQuery } from "../types";

export function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [contract, setContract] = useState<Contract | null>(null);
  const [clauses, setClauses] = useState<ContractClause[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<ContractQuery | null>(null);
  const [error, setError] = useState("");

  async function load() {
    const [contractResponse, clausesResponse] = await Promise.all([
      api.get<Contract>(`/contracts/${id}/`),
      api.get<ContractClause[]>(`/contracts/${id}/clauses/`),
    ]);
    setContract(contractResponse.data);
    setClauses(clausesResponse.data);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleAsk(event: FormEvent) {
    event.preventDefault();
    setAsking(true);
    setError("");
    setAnswer(null);
    try {
      const response = await api.post<ContractQuery>("/queries/", {
        question_text: question,
        contract_id: Number(id),
      });
      setAnswer(response.data);
      setQuestion("");
    } catch {
      setError("Could not get an answer. Has this contract been processed yet?");
    } finally {
      setAsking(false);
    }
  }

  if (!contract) return <div className="page">Loading...</div>;

  return (
    <div className="page">
      <h2>{contract.title}</h2>
      <p className="contract-meta">
        {contract.counterparty} &middot; {contract.contract_type} &middot;{" "}
        <span className={`status-badge status-${contract.status}`}>{contract.status}</span>
      </p>

      <section className="ask-section">
        <h3>Ask a question about this contract</h3>
        <form onSubmit={handleAsk} className="form-row">
          <input
            placeholder="e.g. What is the termination notice period?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
          />
          <button type="submit" disabled={asking || contract.status !== "processed"}>
            {asking ? "Asking..." : "Ask"}
          </button>
        </form>
        {contract.status !== "processed" && (
          <p className="hint">Process this contract before asking questions about it.</p>
        )}
        {error && <div className="error-banner">{error}</div>}
        {answer && (
          <div className="answer-card">
            <strong>Answer</strong>
            <p>{answer.answer_text}</p>
            <small>Retrieved chunk ids: {answer.retrieved_chunk_ids.join(", ") || "none"}</small>
          </div>
        )}
      </section>

      <section>
        <h3>Extracted clauses ({clauses.length})</h3>
        <table className="data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Page</th>
              <th>Risky</th>
              <th>Text</th>
            </tr>
          </thead>
          <tbody>
            {clauses.map((clause) => (
              <tr key={clause.id} className={clause.is_risky ? "risky-row" : ""}>
                <td>{clause.clause_type}</td>
                <td>{clause.page_number}</td>
                <td>{clause.is_risky ? "Yes" : "No"}</td>
                <td>{clause.extracted_text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
