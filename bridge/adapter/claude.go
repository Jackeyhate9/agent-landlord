package adapter

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os/exec"
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
