package join

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

type Request struct {
	ProtocolVersion int    `json:"protocol_version"`
	JoinCode        string `json:"join_code"`
	PublicKey       string `json:"public_key"`
	Signature       string `json:"signature"`
	Adapter         string `json:"adapter"`
	// 隐私友好的自动检测上报：只包含运行时类型名与模型名标签，
	// 不含任何路径、密钥、主机名或其他本机信息。
	DetectedRuntime string `json:"detected_runtime,omitempty"`
	DetectedModel   string `json:"detected_model,omitempty"`
}
type Session struct {
	AgentID      string `json:"agent_id"`
	SessionToken string `json:"session_token"`
	ResumeID     string `json:"resume_id"`
	WebSocketURL string `json:"websocket_url"`
}

func Exchange(ctx context.Context, baseURL string, request Request, client *http.Client) (Session, error) {
	b, _ := json.Marshal(request)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimRight(baseURL, "/")+"/api/agent/join", bytes.NewReader(b))
	if err != nil {
		return Session{}, err
	}
	req.Header.Set("Content-Type", "application/json")
	if client == nil {
		client = &http.Client{Timeout: 10 * 1e9}
	}
	res, err := client.Do(req)
	if err != nil {
		return Session{}, err
	}
	defer res.Body.Close()
	if res.StatusCode/100 != 2 {
		return Session{}, fmt.Errorf("join failed: %s", res.Status)
	}
	var session Session
	if err := json.NewDecoder(res.Body).Decode(&session); err != nil {
		return Session{}, err
	}
	if session.SessionToken == "" || session.WebSocketURL == "" {
		return Session{}, fmt.Errorf("join response missing session_token or websocket_url")
	}
	return session, nil
}
