package client

import (
	"context"
	"encoding/json"
	"fmt"
	"math/rand"
	"time"

	"agent-landlord/bridge/adapter"
	"agent-landlord/bridge/protocol"
)

type Envelope struct {
	Type            string                `json:"type"`
	ProtocolVersion int                   `json:"protocol_version,omitempty"`
	SessionToken    string                `json:"session_token,omitempty"`
	ResumeID        string                `json:"resume_id,omitempty"`
	Observation     *protocol.Observation `json:"observation,omitempty"`
	Action          *protocol.Action      `json:"action,omitempty"`
	Message         string                `json:"message,omitempty"`
}
type Socket interface {
	Read(context.Context) ([]byte, error)
	Write(context.Context, []byte) error
	Ping(context.Context) error
	Close() error
}
type DialFunc func(context.Context, string, string) (Socket, error)
type Runner struct {
	URL, SessionToken, ResumeID       string
	Adapter                           adapter.Adapter
	Dial                              DialFunc
	Heartbeat, MinBackoff, MaxBackoff time.Duration
	OnAction                          func()
}

func (r *Runner) Run(ctx context.Context) error {
	if r.Adapter == nil {
		return fmt.Errorf("adapter is required")
	}
	if r.Dial == nil {
		r.Dial = DialWebSocket
	}
	if r.Heartbeat == 0 {
		r.Heartbeat = 20 * time.Second
	}
	if r.MinBackoff == 0 {
		r.MinBackoff = time.Second
	}
	if r.MaxBackoff == 0 {
		r.MaxBackoff = 30 * time.Second
	}
	backoff := r.MinBackoff
	for {
		if err := ctx.Err(); err != nil {
			return err
		}
		sock, err := r.Dial(ctx, r.URL, r.SessionToken)
		if err == nil {
			err = r.serve(ctx, sock)
			sock.Close()
			// Successful session resets backoff so next disconnect retries quickly
			if err == nil {
				backoff = r.MinBackoff
			}
		}
		if ctx.Err() != nil {
			return ctx.Err()
		}
		delay := backoff + time.Duration(rand.Int63n(int64(backoff/4+1)))
		timer := time.NewTimer(delay)
		select {
		case <-ctx.Done():
			timer.Stop()
			return ctx.Err()
		case <-timer.C:
		}
		backoff *= 2
		if backoff > r.MaxBackoff {
			backoff = r.MaxBackoff
		}
		_ = err
	}
}
func (r *Runner) serve(ctx context.Context, s Socket) error {
	hello := Envelope{Type: "hello", ProtocolVersion: 1, SessionToken: r.SessionToken}
	if r.ResumeID != "" {
		hello.Type = "resume"
		hello.ResumeID = r.ResumeID
	}
	if err := writeJSON(ctx, s, hello); err != nil {
		return err
	}
	pingCtx, cancel := context.WithCancel(ctx)
	defer cancel()
	go func() {
		ticker := time.NewTicker(r.Heartbeat)
		defer ticker.Stop()
		for {
			select {
			case <-pingCtx.Done():
				return
			case <-ticker.C:
				if s.Ping(pingCtx) != nil {
					_ = s.Close()
					return
				}
			}
		}
	}()
	for {
		b, err := s.Read(ctx)
		if err != nil {
			return err
		}
		var m Envelope
		if err := json.Unmarshal(b, &m); err != nil {
			return fmt.Errorf("decode gateway message: %w", err)
		}
		switch m.Type {
		case "session":
			if m.ResumeID != "" {
				r.ResumeID = m.ResumeID
			}
		case "ping":
			if err := writeJSON(ctx, s, Envelope{Type: "pong"}); err != nil {
				return err
			}
		case "observation":
			if m.Observation == nil {
				return fmt.Errorf("observation payload missing")
			}
			if err := protocol.ValidateObservation(*m.Observation); err != nil {
				return err
			}
			timeout := time.Duration(m.Observation.DecisionTimeoutMS) * time.Millisecond
			if timeout <= 0 {
				timeout = 8 * time.Second
			}
			actCtx, cancel := context.WithTimeout(ctx, timeout)
			action, err := r.Adapter.Act(actCtx, *m.Observation)
			cancel()
			if err != nil {
				return fmt.Errorf("adapter act: %w", err)
			}
			if err := protocol.ValidateAction(*m.Observation, action); err != nil {
				return err
			}
			if err := writeJSON(ctx, s, Envelope{Type: "action", ProtocolVersion: 1, Action: &action}); err != nil {
				return err
			}
			if r.OnAction != nil {
				r.OnAction()
			}
		case "error":
			return fmt.Errorf("gateway: %s", m.Message)
		}
	}
}
func writeJSON(ctx context.Context, s Socket, v any) error {
	b, err := json.Marshal(v)
	if err != nil {
		return err
	}
	return s.Write(ctx, b)
}
