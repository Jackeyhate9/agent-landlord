package adapter

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"

	"agent-landlord/bridge/protocol"
)

func observation() protocol.Observation {
	return protocol.Observation{ProtocolVersion: 1, GameID: "g", TurnID: "t", Seat: "landlord", LegalActions: []protocol.LegalAction{{ID: 18}}}
}

func TestCustomHTTPPostsObservationAndReturnsValidatedAction(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var obs protocol.Observation
		if err := json.NewDecoder(r.Body).Decode(&obs); err != nil || obs.TurnID != "t" {
			t.Fatalf("bad observation: %#v %v", obs, err)
		}
		fmt.Fprint(w, `{"action_id":18}`)
	}))
	defer server.Close()
	a := &HTTPAdapter{URL: server.URL, Client: server.Client()}
	got, err := a.Act(context.Background(), observation())
	if err != nil {
		t.Fatal(err)
	}
	if got.ActionID != 18 || got.GameID != "g" {
		t.Fatalf("unexpected action: %#v", got)
	}
}

func TestCustomCLIUsesStdinAndStdout(t *testing.T) {
	a := &CLIAdapter{Command: []string{os.Args[0], "-test.run=TestCLIHelperProcess", "--"}}
	a.Env = append(os.Environ(), "GO_WANT_CLI_HELPER=1")
	got, err := a.Act(context.Background(), observation())
	if err != nil {
		t.Fatal(err)
	}
	if got.ActionID != 18 {
		t.Fatalf("unexpected action: %#v", got)
	}
}

func TestCLIHelperProcess(t *testing.T) {
	if os.Getenv("GO_WANT_CLI_HELPER") != "1" {
		return
	}
	b, _ := io.ReadAll(os.Stdin)
	if !bytes.Contains(b, []byte(`"turn_id":"t"`)) {
		os.Exit(3)
	}
	fmt.Print(`{"action_id":18}`)
	os.Exit(0)
}

func TestOllamaDiscoversModelsAndActs(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/tags" {
			fmt.Fprint(w, `{"models":[{"name":"qwen:latest"}]}`)
			return
		}
		fmt.Fprint(w, `{"message":{"content":"{\"action_id\":18}"}}`)
	}))
	defer server.Close()
	a := &OllamaAdapter{BaseURL: server.URL, Client: server.Client()}
	models, err := a.Models(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if len(models) != 1 || models[0] != "qwen:latest" {
		t.Fatalf("unexpected models: %#v", models)
	}
	a.Model = models[0]
	got, err := a.Act(context.Background(), observation())
	if err != nil {
		t.Fatal(err)
	}
	if got.ActionID != 18 {
		t.Fatalf("unexpected action: %#v", got)
	}
}

func TestOpenAICompatibleKeepsCredentialOnLocalRequest(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer local-secret" {
			t.Fatalf("missing local credential")
		}
		fmt.Fprint(w, `{"choices":[{"message":{"content":"{\"action_id\":18}"}}]}`)
	}))
	defer server.Close()
	a := &OpenAICompatibleAdapter{BaseURL: server.URL, APIKey: "local-secret", Model: "local-model", Client: server.Client()}
	got, err := a.Act(context.Background(), observation())
	if err != nil {
		t.Fatal(err)
	}
	if got.ActionID != 18 {
		t.Fatalf("unexpected action: %#v", got)
	}
}

func TestCodexUsesExecJSONAndParsesFinalAgentMessage(t *testing.T) {
	a := &CodexCLI{Binary: "codex", Run: func(_ context.Context, name string, args ...string) ([]byte, []byte, error) {
		joined := strings.Join(args, " ")
		if name != "codex" || !strings.Contains(joined, "exec") ||
			!strings.Contains(joined, "--json") ||
			!strings.Contains(joined, "--sandbox read-only") {
			t.Fatalf("unexpected codex invocation: %s %s", name, joined)
		}
		return []byte("{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"{\\\"action_id\\\":18}\"}}\n"), nil, nil
	}}
	got, err := a.Act(context.Background(), observation())
	if err != nil {
		t.Fatal(err)
	}
	if got.ActionID != 18 || got.TurnID != "t" {
		t.Fatalf("unexpected action: %#v", got)
	}
}
