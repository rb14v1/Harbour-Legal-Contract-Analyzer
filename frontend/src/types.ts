export type Role = "legal_reviewer" | "admin";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  date_joined: string;
}

export type ContractType =
  | "nda"
  | "msa"
  | "employment"
  | "lease"
  | "licensing"
  | "vendor"
  | "other";

export type ContractStatus = "uploaded" | "processing" | "processed" | "failed";

export interface Contract {
  id: number;
  title: string;
  counterparty: string;
  contract_type: ContractType;
  effective_date: string | null;
  expiry_date: string | null;
  uploaded_by: number;
  uploaded_by_email: string;
  blob_path: string;
  status: ContractStatus;
  created_at: string;
  clause_count: number;
  chunk_count: number;
}

export interface ContractClause {
  id: number;
  contract: number;
  clause_type: string;
  extracted_text: string;
  page_number: number;
  is_risky: boolean;
}

export interface ContractQuery {
  id: number;
  asked_by: number;
  asked_by_email: string;
  contract: number | null;
  question_text: string;
  answer_text: string;
  retrieved_chunk_ids: number[];
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
