import { type FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";
import type { Contract, ContractType, Paginated } from "../types";

const CONTRACT_TYPES: ContractType[] = [
  "nda", "msa", "employment", "lease", "licensing", "vendor", "other",
];

export function ContractsPage() {
  const { user } = useAuth();
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [title, setTitle] = useState("");
  const [counterparty, setCounterparty] = useState("");
  const [contractType, setContractType] = useState<ContractType>("other");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [processingId, setProcessingId] = useState<number | null>(null);

  async function loadContracts() {
    setLoading(true);
    try {
      const response = await api.get<Paginated<Contract>>("/contracts/");
      setContracts(response.data.results);
    } catch {
      setError("Could not load contracts.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadContracts();
  }, []);

  async function handleUpload(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    setUploading(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title);
      formData.append("counterparty", counterparty);
      formData.append("contract_type", contractType);
      await api.post("/contracts/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setTitle("");
      setCounterparty("");
      setContractType("other");
      setFile(null);
      await loadContracts();
    } catch {
      setError("Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleProcess(contractId: number) {
    setProcessingId(contractId);
    try {
      await api.post(`/contracts/${contractId}/process/`);
      await loadContracts();
    } catch {
      setError("Processing failed.");
    } finally {
      setProcessingId(null);
    }
  }

  async function handleDelete(contractId: number) {
    if (!confirm("Delete this contract? This cannot be undone.")) return;
    try {
      await api.delete(`/contracts/${contractId}/`);
      await loadContracts();
    } catch {
      setError("Delete failed (admin only).");
    }
  }

  return (
    <div className="page">
      <h2>Contracts</h2>
      {error && <div className="error-banner">{error}</div>}

      <form className="upload-form" onSubmit={handleUpload}>
        <h3>Upload a new contract</h3>
        <div className="form-row">
          <input placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <input
            placeholder="Counterparty"
            value={counterparty}
            onChange={(e) => setCounterparty(e.target.value)}
            required
          />
          <select value={contractType} onChange={(e) => setContractType(e.target.value as ContractType)}>
            {CONTRACT_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} required />
          <button type="submit" disabled={uploading}>
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </div>
      </form>

      {loading ? (
        <p>Loading contracts...</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Counterparty</th>
              <th>Type</th>
              <th>Status</th>
              <th>Clauses</th>
              <th>Chunks</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {contracts.map((contract) => (
              <tr key={contract.id}>
                <td>
                  <Link to={`/contracts/${contract.id}`}>{contract.title}</Link>
                </td>
                <td>{contract.counterparty}</td>
                <td>{contract.contract_type}</td>
                <td>
                  <span className={`status-badge status-${contract.status}`}>{contract.status}</span>
                </td>
                <td>{contract.clause_count}</td>
                <td>{contract.chunk_count}</td>
                <td className="actions-cell">
                  {contract.status !== "processed" && (
                    <button onClick={() => handleProcess(contract.id)} disabled={processingId === contract.id}>
                      {processingId === contract.id ? "Processing..." : "Process"}
                    </button>
                  )}
                  {user?.role === "admin" && (
                    <button className="danger" onClick={() => handleDelete(contract.id)}>
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
