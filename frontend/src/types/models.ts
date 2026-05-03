export interface Paper {
  topics: Topic[];
  id: number;
  title: string;
  year: number | null;
  authors: string[];
  multi_label: string[] | null;
  predicted_multi_labels: string[];
  citation_count: number;
  doi: string;
}

export interface PaperDetail extends Paper {
  abstract: string | null;
  venue: string | null;
  url: string | null;
  topic_distribution: number[];
  entropy: number | null;
}

export interface Topic {
  id: number;
  name: string;
  keywords: string[];
}

export interface Author {
  id: string;
  name: string;
  works_count: number;
  institution: string | null;
  faculty: string | null;
  department: string | null;
  primary_cluster: string | null;
  // Use Record<string, number> Replace TS with an Object for {"Math": 10, "CS": 5}
  topic_profile: Record<string, number> | null;
}

export interface DashboardSummary {
  total_papers: number;
  total_authors: number;
  total_clusters: number;
}

export interface DomainInfo {
  fullKey: string;
  name: string; // ใช้เก็บชื่อ Topic แบบเต็มไปเลย
  keywords: string[];
}
