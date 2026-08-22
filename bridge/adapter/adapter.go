package adapter

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"strings"
	"time"

	"agent-landlord/bridge/protocol"
)

func isLocalHost(raw string) bool {
	u, err := url.Parse(raw)
	if err != nil {
		return false
	}
	host := u.Hostname()
	if host == "" {
		return false
	}
	if host == "localhost" || host == "127.0.0.1" || host == "::1" {
		return true
	}
	// Allow explicit opt-in via ARENA_ALLOW_REMOTE=1 for testing
	if os.Getenv("ARENA_ALLOW_REMOTE") == "1" {
		return true
	}
	return false
}

func newLocalClient() *http.Client {
	return &http.Client{
		Timeout: 10 * time.Second,
		Transport: &http.Transport{
			DialContext: func(ctx context.Context, network, addr string) (net.Conn, error) {
				return (&net.Dialer{Timeout: 5 * time.Second}).DialContext(ctx, network, addr)
			},
		},
	}
}

type Adapter interface {
	Name() string
	Act(context.Context, protocol.Observation) (protocol.Action, error)
}

func decode(obs protocol.Observation, r io.Reader) (protocol.Action, error) {
	b, err := io.ReadAll(io.LimitReader(r, 64<<10))
	if err != nil {
		return protocol.Action{}, err
	}
	return protocol.NormalizeAction(obs, b)
}

type CLIAdapter struct{ Command, Env []string }

func (a *CLIAdapter) Name() string { return "custom-cli" }
func (a *CLIAdapter) Act(ctx context.Context, obs protocol.Observation) (protocol.Action, error) {
	if len(a.Command) == 0 {
		return protocol.Action{}, fmt.Errorf("custom CLI command is empty")
	}
	b, _ := json.Marshal(obs)
	cmd := exec.CommandContext(ctx, a.Command[0], a.Command[1:]...)
	cmd.Stdin = bytes.NewReader(b)
	if a.Env != nil {
		cmd.Env = a.Env
	} else {
		cmd.Env = os.Environ()
	}
	out, err := cmd.Output()
	if err != nil {
		return protocol.Action{}, fmt.Errorf("custom CLI: %w", err)
	}
	return protocol.NormalizeAction(obs, out)
}

type HTTPAdapter struct {
	URL, BearerToken string
	Client           *http.Client
}

func (a *HTTPAdapter) Name() string { return "custom-http" }
func (a *HTTPAdapter) Act(ctx context.Context, obs protocol.Observation) (protocol.Action, error) {
	if !isLocalHost(a.URL) {
		return protocol.Action{}, fmt.Errorf("custom HTTP URL must be localhost (got %s); set ARENA_ALLOW_REMOTE=1 to override", a.URL)
	}
	b, _ := json.Marshal(obs)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, a.URL, bytes.NewReader(b))
	if err != nil {
		return protocol.Action{}, err
	}
	req.Header.Set("Content-Type", "application/json")
	if a.BearerToken != "" {
		req.Header.Set("Authorization", "Bearer "+a.BearerToken)
	}
	c := a.Client
	if c == nil {
		c = newLocalClient()
	}
	res, err := c.Do(req)
	if err != nil {
		return protocol.Action{}, err
	}
	defer func() { io.Copy(io.Discard, res.Body); res.Body.Close() }()
	if res.StatusCode/100 != 2 {
		return protocol.Action{}, fmt.Errorf("agent HTTP status %s", res.Status)
	}
	return decode(obs, res.Body)
}

type OllamaAdapter struct {
	BaseURL, Model string
	Client         *http.Client
}

func (a *OllamaAdapter) Name() string { return "ollama" }
func (a *OllamaAdapter) client() *http.Client {
	if a.Client != nil {
		return a.Client
	}
	return newLocalClient()
}
func (a *OllamaAdapter) base() string {
	if a.BaseURL != "" {
		return strings.TrimRight(a.BaseURL, "/")
	}
	return "http://localhost:11434"
}
func (a *OllamaAdapter) Models(ctx context.Context) ([]string, error) {
	if !isLocalHost(a.base()) {
		return nil, fmt.Errorf("Ollama URL must be localhost (got %s)", a.base())
	}
	req, _ := http.NewRequestWithContext(ctx, http.MethodGet, a.base()+"/api/tags", nil)
	res, err := a.client().Do(req)
	if err != nil {
		return nil, err
	}
	defer func() { io.Copy(io.Discard, res.Body); res.Body.Close() }()
	var body struct {
		Models []struct {
			Name string `json:"name"`
		} `json:"models"`
	}
	if err := json.NewDecoder(res.Body).Decode(&body); err != nil {
		return nil, err
	}
	models := make([]string, 0, len(body.Models))
	for _, m := range body.Models {
		models = append(models, m.Name)
	}
	return models, nil
}
func (a *OllamaAdapter) Act(ctx context.Context, obs protocol.Observation) (protocol.Action, error) {
	if a.Model == "" {
		return protocol.Action{}, fmt.Errorf("Ollama model is required")
	}
	if !isLocalHost(a.base()) {
		return protocol.Action{}, fmt.Errorf("Ollama URL must be localhost (got %s)", a.base())
	}
	ob, _ := json.Marshal(obs)
	prompt := "Return only a JSON Agent Landlord action with action_id and optional public_comment. Never include hidden reasoning. Observation:\n" + string(ob)
	body, _ := json.Marshal(map[string]any{"model": a.Model, "stream": false, "format": "json", "messages": []map[string]string{{"role": "user", "content": prompt}}})
	req, _ := http.NewRequestWithContext(ctx, http.MethodPost, a.base()+"/api/chat", bytes.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	res, err := a.client().Do(req)
	if err != nil {
		return protocol.Action{}, err
	}
	defer func() { io.Copy(io.Discard, res.Body); res.Body.Close() }()
	if res.StatusCode/100 != 2 {
		return protocol.Action{}, fmt.Errorf("Ollama status %s", res.Status)
	}
	var out struct {
		Message struct {
			Content string `json:"content"`
		} `json:"message"`
	}
	if err := json.NewDecoder(res.Body).Decode(&out); err != nil {
		return protocol.Action{}, err
	}
	return protocol.NormalizeAction(obs, []byte(out.Message.Content))
}
