package adapter

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"os/exec"

	"agent-landlord/bridge/protocol"
)

// CodexCLI uses the non-interactive Codex exec contract. It is intentionally
// separate from ClaudeCLI because the two CLIs do not share flags or output.
type CodexCLI struct {
	Binary, Model string
	Run           func(context.Context, string, ...string) ([]byte, []byte, error)
}

func (a *CodexCLI) Name() string { return "codex" }

func (a *CodexCLI) Act(ctx context.Context, obs protocol.Observation) (protocol.Action, error) {
	bin := a.Binary
	if bin == "" {
		bin = "codex"
	}
	observation, _ := json.Marshal(obs)
	prompt := "Choose exactly one legal Agent Landlord action. Return only JSON with action_id and optional public_comment. Never reveal chain of thought. Observation: " + string(observation)
	args := []string{
		"exec", "--ephemeral", "--skip-git-repo-check",
		"--sandbox", "read-only", "--json",
	}
	if a.Model != "" {
		args = append(args, "--model", a.Model)
	}
	args = append(args, prompt)
	var out, stderrBytes []byte
	var err error
	if a.Run != nil {
		out, stderrBytes, err = a.Run(ctx, bin, args...)
	} else {
		cmd := exec.CommandContext(ctx, bin, args...)
		var stderr bytes.Buffer
		cmd.Stderr = &stderr
		out, err = cmd.Output()
		stderrBytes = stderr.Bytes()
	}
	if err != nil {
		return protocol.Action{}, fmt.Errorf("codex CLI: %w: %s", err, string(stderrBytes))
	}

	var finalText string
	scanner := bufio.NewScanner(bytes.NewReader(out))
	scanner.Buffer(make([]byte, 1024), 1024*1024)
	for scanner.Scan() {
		var event struct {
			Type string `json:"type"`
			Item struct {
				Type string `json:"type"`
				Text string `json:"text"`
			} `json:"item"`
		}
		if json.Unmarshal(scanner.Bytes(), &event) == nil &&
			event.Type == "item.completed" &&
			event.Item.Type == "agent_message" &&
			event.Item.Text != "" {
			finalText = event.Item.Text
		}
	}
	if err := scanner.Err(); err != nil {
		return protocol.Action{}, fmt.Errorf("decode codex JSONL: %w", err)
	}
	if finalText == "" {
		return protocol.Action{}, fmt.Errorf("codex CLI returned no final agent message")
	}
	return protocol.NormalizeAction(obs, []byte(finalText))
}
