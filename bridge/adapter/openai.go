package adapter

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"agent-landlord/bridge/protocol"
)

type OpenAICompatibleAdapter struct {
	BaseURL, APIKey, Model string
	Client                 *http.Client
}

func (a *OpenAICompatibleAdapter) Name() string { return "openai-compatible" }
func (a *OpenAICompatibleAdapter) Act(ctx context.Context, obs protocol.Observation) (protocol.Action, error) {
	if a.BaseURL == "" || a.Model == "" {
		return protocol.Action{}, fmt.Errorf("MODEL_BASE_URL and MODEL_NAME are required")
	}
	ob, _ := json.Marshal(obs)
	prompt := "Choose one legal action. Return only JSON with action_id and optional public_comment; public_comment is public, never chain of thought. Observation:\n" + string(ob)
	body, _ := json.Marshal(map[string]any{"model": a.Model, "messages": []map[string]string{{"role": "user", "content": prompt}}, "response_format": map[string]string{"type": "json_object"}})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimRight(a.BaseURL, "/")+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return protocol.Action{}, err
	}
	req.Header.Set("Content-Type", "application/json")
	if a.APIKey != "" {
		req.Header.Set("Authorization", "Bearer "+a.APIKey)
	}
	c := a.Client
	if c == nil {
		c = http.DefaultClient
	}
	res, err := c.Do(req)
	if err != nil {
		return protocol.Action{}, err
	}
	defer res.Body.Close()
	if res.StatusCode/100 != 2 {
		return protocol.Action{}, fmt.Errorf("OpenAI-compatible status %s", res.Status)
	}
	var out struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}
	if err := json.NewDecoder(res.Body).Decode(&out); err != nil {
		return protocol.Action{}, err
	}
	if len(out.Choices) == 0 {
		return protocol.Action{}, fmt.Errorf("empty completion")
	}
	return protocol.NormalizeAction(obs, []byte(out.Choices[0].Message.Content))
}
