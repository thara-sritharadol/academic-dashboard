export interface Paper {
  id: string;
  title: string;
  year: number | null;
  cluster_id: number | null;
  cluster_label: string | null;
  predicted_multi_labels: string[];
  authors_list?: string[];
  citation_count: number;
}

export interface PaperDetail extends Paper {
  abstract: string | null;
  doi: string;
  venue: string | null;
  url: string | null;
  topic_distribution: number[];
  entropy: number | null;
  authors: Author[];
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
