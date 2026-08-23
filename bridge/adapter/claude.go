package adapter

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"time"

	"agent-landlord/bridge/protocol"
)

// ClaudeCLI uses only flags verified from `claude --help` on 2026-08-22.
type ClaudeCLI struct{ Binary, Model string }

func (a *ClaudeCLI) Name() string { return "claude-code" }
func (a *ClaudeCLI) Act(ctx context.Context, obs protocol.Observation) (protocol.Action, error) {
	bin := a.Binary
	if bin == "" {
		bin = "claude"
	}
	ob, _ := json.Marshal(obs)
	schema := `{"type":"object","properties":{"action_id":{"type":"integer"},"public_comment":{"type":"string"}},"required":["action_id"],"additionalProperties":false}`
	args := []string{"-p", "--output-format", "json", "--json-schema", schema, "Return only the requested Agent Landlord action. Do not reveal chain of thought. Observation: " + string(ob)}
	if a.Model != "" {
		args = append([]string{"--model", a.Model}, args...)
	}
	cmd := exec.CommandContext(ctx, bin, args...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	out, err := cmd.Output()
	if err != nil {
		return protocol.Action{}, fmt.Errorf("claude CLI: %w: %s", err, stderr.String())
	}
	var envelope struct {
		StructuredOutput json.RawMessage `json:"structured_output"`
		Result           string          `json:"result"`
	}
	if json.Unmarshal(out, &envelope) == nil {
		if len(envelope.StructuredOutput) > 0 {
			return protocol.NormalizeAction(obs, envelope.StructuredOutput)
		}
		if envelope.Result != "" {
			return protocol.NormalizeAction(obs, []byte(envelope.Result))
		}
	}
	return protocol.NormalizeAction(obs, out)
}

type Detection struct {
	Name      string `json:"name"`
	Available bool   `json:"available"`
	Note      string `json:"note"`
}

func DetectCLIs() []Detection {
	dets := []Detection{
		detect("codex", "Codex"),
		detect("claude", "Claude Code"),
	}
	// Ollama detection via localhost:11434 health
	if available := detectOllama(); available {
		dets = append(dets, Detection{Name: "ollama", Available: true, Note: "Ollama detected (localhost:11434)"})
	} else {
		dets = append(dets, Detection{Name: "ollama", Available: false, Note: "Ollama not detected (localhost:11434)"})
	}
	return dets
}
func detect(name, note string) Detection {
	_, err := exec.LookPath(name)
	if err == nil {
		return Detection{Name: name, Available: true, Note: note + " detected"}
	}
	return Detection{Name: name, Available: false, Note: note + " not detected"}
}
func detectOllama() bool {
	client := &http.Client{Timeout: 400 * time.Millisecond}
	resp, err := client.Get("http://localhost:11434/api/tags")
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode/100 == 2
}

// DetectDefault 返回 (运行时名, 模型名标签, 是否找到)。
// 只依据公开可见的信号：CLI 是否在 PATH、环境变量是否声明了模型、Ollama 本机接口。
// 绝不读取文件内容、密钥或系统路径。
func DetectDefault() (string, string, bool) {
	// 环境变量优先（用户显式声明的模型名）
	if m := os.Getenv("MODEL_NAME"); m != "" {
		if os.Getenv("MODEL_BASE_URL") != "" || os.Getenv("MODEL_API_KEY") != "" {
			return "openai-compatible", sanitizeModel(m), true
		}
	}
	dets := DetectCLIs()
	for _, d := range dets {
		if !d.Available {
			continue
		}
		switch d.Name {
		case "codex":
			return "codex", "Codex", true
		case "claude":
			return "claude-code", "Claude Code", true
		case "ollama":
			return "ollama", ollamaDefaultModel(), true
		}
	}
	return "", "", false
}

func ollamaDefaultModel() string {
	client := &http.Client{Timeout: 800 * time.Millisecond}
	resp, err := client.Get("http://localhost:11434/api/tags")
	if err != nil {
		return "Ollama"
	}
	defer resp.Body.Close()
	var body struct {
		Models []struct{ Name string `json:"name"` } `json:"models"`
	}
	if json.NewDecoder(resp.Body).Decode(&body) != nil || len(body.Models) == 0 {
		return "Ollama"
	}
	return sanitizeModel(body.Models[0].Name)
}

// sanitizeModel 只保留模型名的可展示部分（去掉 tag 后的摘要等），限长 24。
func sanitizeModel(m string) string {
	m = strings.TrimSpace(m)
	for i := 0; i < len(m); i++ {
		c := m[i]
		if !(c >= 'a' && c <= 'z' || c >= 'A' && c <= 'Z' || c >= '0' && c <= '9' ||
			c == '-' || c == '.' || c == '_' || c == ':' || c == ' ') {
			m = m[:i]
			break
		}
	}
	m = strings.TrimSpace(m)
	if len(m) > 24 {
		m = m[:24]
	}
	if m == "" {
		return "Custom"
	}
	return m
}
