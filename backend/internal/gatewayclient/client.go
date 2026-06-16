package gatewayclient

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"
)

type Client struct {
	baseURL string
	http    *http.Client
}

type Health struct {
	Status    string         `json:"status"`
	Provider  string         `json:"provider"`
	Upstreams map[string]any `json:"upstreams"`
}

func New(baseURL string) Client {
	return Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		http:    &http.Client{Timeout: 10 * time.Second},
	}
}

func (c Client) Health(ctx context.Context) (Health, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+"/health", nil)
	if err != nil {
		return Health{}, err
	}
	res, err := c.http.Do(req)
	if err != nil {
		return Health{}, err
	}
	defer res.Body.Close()
	if res.StatusCode >= 300 {
		return Health{}, fmt.Errorf("gateway health returned %s", res.Status)
	}
	var health Health
	if err := json.NewDecoder(res.Body).Decode(&health); err != nil {
		return Health{}, err
	}
	return health, nil
}

func (c Client) Check(ctx context.Context) error {
	_, err := c.Health(ctx)
	return err
}
