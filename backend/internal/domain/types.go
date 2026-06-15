package domain

import "time"

const ResearchDisclaimer = "This output is research assistance only and does not constitute investment advice."

type Holding struct {
	Ticker      string  `json:"ticker"`
	Company     string  `json:"company"`
	Shares      float64 `json:"shares"`
	MarketValue float64 `json:"market_value"`
	Weight      float64 `json:"weight"`
	Sector      string  `json:"sector"`
}

type Portfolio struct {
	ID         string    `json:"id"`
	Name       string    `json:"name"`
	TotalValue float64   `json:"total_value"`
	Holdings   []Holding `json:"holdings"`
	Disclaimer string    `json:"disclaimer"`
}

type Filing struct {
	ID         string `json:"id"`
	Ticker     string `json:"ticker"`
	FilingType string `json:"filing_type"`
	Year       int    `json:"year"`
	Section    string `json:"section"`
	SourceURL  string `json:"source_url"`
}

type EvidenceCitation struct {
	ID         string `json:"id"`
	Ticker     string `json:"ticker"`
	Anchor     string `json:"anchor"`
	FilingType string `json:"filing_type"`
	Year       int    `json:"year"`
	Section    string `json:"section"`
	Excerpt    string `json:"excerpt"`
	SourceURL  string `json:"source_url"`
}

type DisclosureChange struct {
	ID          string   `json:"id"`
	Ticker      string   `json:"ticker"`
	Section     string   `json:"section"`
	FromYear    int      `json:"from_year"`
	ToYear      int      `json:"to_year"`
	ChangeType  string   `json:"change_type"`
	Materiality string   `json:"materiality"`
	Confidence  float64  `json:"confidence"`
	Summary     string   `json:"summary"`
	OldText     string   `json:"old_text"`
	NewText     string   `json:"new_text"`
	CitationIDs []string `json:"citation_ids"`
}

type RiskDriver struct {
	Category    string   `json:"category"`
	Score       int      `json:"score"`
	Summary     string   `json:"summary"`
	CitationIDs []string `json:"citation_ids"`
}

type RiskScore struct {
	Ticker        string       `json:"ticker"`
	Score         int          `json:"score"`
	Delta         int          `json:"delta"`
	ExposureLevel string       `json:"exposure_level"`
	Weight        float64      `json:"weight"`
	TopDriver     string       `json:"top_driver"`
	Drivers       []RiskDriver `json:"drivers"`
}

type MemoChange struct {
	Ticker      string   `json:"ticker"`
	Section     string   `json:"section"`
	Summary     string   `json:"summary"`
	CitationIDs []string `json:"citation_ids"`
}

type AnalystMemo struct {
	ExecutiveSummary string       `json:"executive_summary"`
	ExposureAffected []Holding    `json:"exposure_affected"`
	TopChanges       []MemoChange `json:"top_changes"`
	RiskScores       []RiskScore  `json:"risk_scores"`
	Watchlist        []string     `json:"watchlist"`
	Limitations      string       `json:"limitations"`
	Confidence       float64      `json:"confidence"`
	CitationIDs      []string     `json:"citation_ids"`
	Disclaimer       string       `json:"disclaimer"`
}

type Metrics struct {
	Provider              string  `json:"provider"`
	PlannerLatencyMS      int     `json:"planner_latency_ms"`
	MemoLatencyMS         int     `json:"memo_latency_ms"`
	TimeToFirstTokenMS    int     `json:"time_to_first_token_ms"`
	TokensPerSecond       float64 `json:"tokens_per_second"`
	CitationPassRate      float64 `json:"citation_pass_rate"`
	LastPortfolioAnalysis string  `json:"last_portfolio_analysis"`
}

type AgentStage struct {
	ID          string     `json:"id"`
	Label       string     `json:"label"`
	Status      string     `json:"status"`
	StartedAt   *time.Time `json:"started_at,omitempty"`
	CompletedAt *time.Time `json:"completed_at,omitempty"`
	Summary     string     `json:"summary,omitempty"`
}

type AgentRun struct {
	ID                string             `json:"id"`
	Status            string             `json:"status"`
	Question          string             `json:"question"`
	Stages            []AgentStage       `json:"stages"`
	Portfolio         Portfolio          `json:"portfolio"`
	RetrievedEvidence []EvidenceCitation `json:"retrieved_evidence"`
	DisclosureChanges []DisclosureChange `json:"disclosure_changes"`
	RiskScores        []RiskScore        `json:"risk_scores"`
	Memo              *AnalystMemo       `json:"memo,omitempty"`
	Metrics           Metrics            `json:"metrics"`
	CreatedAt         time.Time          `json:"created_at"`
	UpdatedAt         time.Time          `json:"updated_at"`
	Error             string             `json:"error,omitempty"`
}

type ChatAnswer struct {
	Answer     string             `json:"answer"`
	Citations  []EvidenceCitation `json:"citations"`
	Disclaimer string             `json:"disclaimer"`
}
