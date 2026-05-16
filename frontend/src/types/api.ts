export type EligibilityStatus =
  | 'eligible'
  | 'likely_eligible'
  | 'need_more_info'
  | 'not_eligible';

export type Gender = 'male' | 'female' | 'other' | 'prefer_not_to_say';
export type CasteCategory = 'GEN' | 'OBC' | 'SC' | 'ST' | 'EWS';
export type EmploymentStatus = 'employed' | 'unemployed' | 'self_employed' | 'student' | 'retired';
export type MaritalStatus = 'single' | 'married' | 'widowed' | 'divorced';
export type EducationLevel =
  | 'none' | 'primary' | 'secondary' | 'higher_secondary'
  | 'diploma' | 'graduate' | 'postgraduate' | 'masters_degree' | 'phd';

export interface UserProfile {
  age?: number;
  gender?: Gender;
  state?: string;
  district?: string;
  annual_income?: number;
  occupation?: string;
  employment_status?: EmploymentStatus;
  caste_category?: CasteCategory;
  religion?: string;
  marital_status?: MaritalStatus;
  is_farmer?: boolean;
  land_holding_acres?: number;
  education_level?: EducationLevel;
  family_size?: number;
  has_disability?: boolean;
  disability_percentage?: number;
  preferred_language?: string;
}

export interface ProfileResponse {
  profile_id: string;
  created_at: string;
  field_count: number;
}

export interface EligibilityRule {
  rule_type: string;
  operator: string;
  value: Record<string, unknown>;
  logic_group: number;
  is_required: boolean;
  description: string;
  confidence: number;
}

export interface SchemeResultItem {
  scheme_id: number;
  slug: string;
  name: string;
  status: EligibilityStatus;
  score: number;
  semantic_similarity?: number;
  combined_score?: number;
  level: string;
  state?: string;
  categories: string[];
  benefit_type?: string;
  benefit_description?: string;
  application_url?: string;
  missing_fields: string[];
}

export interface SchemeExplanation {
  scheme_id: number;
  slug: string;
  name: string;
  final_rank: number;
  eligibility_verdict: EligibilityStatus;
  confidence: number;
  explanation: string;
  key_benefits: string[];
  action_steps: string[];
  missing_info: string[];
  custom_rule_assessment?: string;
}

export interface PipelineStats {
  stage1_candidates: number;
  stage2_reranked: boolean;
  stage3_explained: boolean;
  total_latency_ms: number;
  stage3_tokens?: number;
}

export interface MatchRequest {
  profile_id?: string;
  profile?: UserProfile;
  query?: string;
  explain?: boolean;
  language?: string;
  max_results?: number;
  include_ineligible?: boolean;
}

export interface MatchResponse {
  profile_id?: string;
  query?: string;
  total_candidates: number;
  results: SchemeResultItem[];
  explanations?: SchemeExplanation[];
  pipeline_stats: PipelineStats;
}

export interface SchemeListItem {
  id: number;
  slug: string;
  name: string;
  level: string;
  state?: string;
  categories: string[];
  benefit_type?: string;
  benefit_amount_min?: number;
  benefit_amount_max?: number;
  ministry?: string;
  application_url?: string;
}

export interface SchemeDetail extends SchemeListItem {
  description?: string;
  benefit_description?: string;
  application_mode?: string;
  documents_required: string[];
  raw_eligibility_text?: string;
  eligibility_rules: EligibilityRule[];
  source_url: string;
  last_updated?: string;
}

export interface PaginatedSchemes {
  items: SchemeListItem[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface SSEEvent {
  type: 'stage1_complete' | 'stage2_complete' | 'stage3_explanation' | 'done' | 'error';
  data: unknown;
}
