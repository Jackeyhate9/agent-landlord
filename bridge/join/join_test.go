package join

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestActivateUsesBearerAndSendsAutomaticQueueConfiguration(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/agents/me/activate" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		if r.Header.Get("Authorization") != "Bearer session-token" {
			t.Fatalf("missing bearer token")
		}
		var got Activation
		if err := json.NewDecoder(r.Body).Decode(&got); err != nil {
			t.Fatal(err)
		}
		if got.AgentName != "StreamBot" || !got.AutoQueue || got.MaxStake != 200 {
			t.Fatalf("unexpected activation: %#v", got)
		}
		w.WriteHeader(http.StatusOK)
	}))
	defer server.Close()

	err := Activate(context.Background(), server.URL, "session-token", Activation{
		AgentName: "StreamBot",
		MaxStake:  200,
		AutoQueue: true,
	}, server.Client())
	if err != nil {
		t.Fatal(err)
	}
}
