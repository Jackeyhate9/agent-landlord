package client

import (
	"context"
	"encoding/json"
	"errors"
	"sync"
	"testing"
	"time"

	"agent-landlord/bridge/protocol"
)

type fakeAdapter struct{}

func (fakeAdapter) Name() string { return "fake" }
func (fakeAdapter) Act(_ context.Context, o protocol.Observation) (protocol.Action, error) {
	return protocol.Action{ProtocolVersion: 1, GameID: o.GameID, TurnID: o.TurnID, ActionID: o.LegalActions[0].ID}, nil
}

type fakeSocket struct {
	reads  [][]byte
	writes [][]byte
	mu     sync.Mutex
}

func (s *fakeSocket) Read(_ context.Context) ([]byte, error) {
	if len(s.reads) == 0 {
		return nil, errors.New("disconnect")
	}
	b := s.reads[0]
	s.reads = s.reads[1:]
	return b, nil
}
func (s *fakeSocket) Write(_ context.Context, b []byte) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.writes = append(s.writes, b)
	return nil
}
func (s *fakeSocket) Ping(context.Context) error { return nil }
func (s *fakeSocket) Close() error               { return nil }

func TestRunReconnectsAndResumesSession(t *testing.T) {
	session, _ := json.Marshal(Envelope{Type: "session", ResumeID: "resume-2"})
	obs, _ := json.Marshal(Envelope{Type: "observation", Observation: &protocol.Observation{ProtocolVersion: 1, GameID: "g", TurnID: "t", Seat: "landlord", LegalActions: []protocol.LegalAction{{ID: 18}}, DecisionTimeoutMS: 1000}})
	s1 := &fakeSocket{}
	s2 := &fakeSocket{reads: [][]byte{session, obs}}
	calls := 0
	activations := 0
	dial := func(context.Context, string, string) (Socket, error) {
		calls++
		if calls == 1 {
			return s1, nil
		}
		return s2, nil
	}
	ctx, cancel := context.WithCancel(context.Background())
	r := Runner{URL: "ws://arena", SessionToken: "memory-only", ResumeID: "resume-1", Adapter: fakeAdapter{}, Dial: dial, MinBackoff: time.Millisecond, MaxBackoff: time.Millisecond, OnAction: func() { cancel() }, OnSession: func() error { activations++; return nil }}
	if err := r.Run(ctx); err != nil && !errors.Is(err, context.Canceled) {
		t.Fatal(err)
	}
	if calls < 2 {
		t.Fatalf("expected reconnect, calls=%d", calls)
	}
	var hello Envelope
	if err := json.Unmarshal(s2.writes[0], &hello); err != nil {
		t.Fatal(err)
	}
	if hello.Type != "resume" || hello.ResumeID != "resume-1" {
		t.Fatalf("missing resume: %#v", hello)
	}
	if activations != 1 || r.ResumeID != "resume-2" {
		t.Fatalf("session activation not applied: activations=%d resume=%s", activations, r.ResumeID)
	}
}
