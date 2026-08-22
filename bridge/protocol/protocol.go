package protocol

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"unicode/utf8"
)

const Version = 1

type LegalAction struct {
	ID    int      `json:"id"`
	Cards []string `json:"cards"`
	Type  string   `json:"type,omitempty"`
	Bid   *int     `json:"bid,omitempty"`
}

type ActionRecord struct {
	Actor    string   `json:"actor,omitempty"`
	ActionID int      `json:"action_id"`
	Cards    []string `json:"cards,omitempty"`
	Type     string   `json:"type,omitempty"`
	Bid      *int     `json:"bid,omitempty"`
}

type Observation struct {
	ProtocolVersion     int            `json:"protocol_version"`
	GameID              string         `json:"game_id"`
	TurnID              string         `json:"turn_id"`
	Phase               string         `json:"phase,omitempty"`
	Seat                string         `json:"seat"`
	SeatIndex           *int           `json:"seat_index,omitempty"`
	Hand                []string       `json:"hand"`
	LandlordCardsPublic []string       `json:"landlord_cards_public"`
	LastAction          *ActionRecord  `json:"last_action,omitempty"`
	ActionHistory       []ActionRecord `json:"action_history"`
	RemainingCardCounts map[string]int `json:"remaining_card_counts"`
	LegalActions        []LegalAction  `json:"legal_actions"`
	BaseStake           int64          `json:"base_stake"`
	CurrentMultiplier   int            `json:"current_multiplier"`
	ArenaTokenBalance   int64          `json:"arena_token_balance"`
	DecisionTimeoutMS   int            `json:"decision_timeout_ms"`
}

type Action struct {
	ProtocolVersion int    `json:"protocol_version"`
	GameID          string `json:"game_id"`
	TurnID          string `json:"turn_id"`
	ActionID        int    `json:"action_id"`
	PublicComment   string `json:"public_comment,omitempty"`
}

func ValidateObservation(o Observation) error {
	if o.ProtocolVersion != Version {
		return fmt.Errorf("unsupported protocol_version %d", o.ProtocolVersion)
	}
	if o.GameID == "" || o.TurnID == "" {
		return errors.New("game_id and turn_id are required")
	}
	roleSeat := o.Seat == "landlord" || o.Seat == "farmer_left" || o.Seat == "farmer_right"
	biddingSeat := o.Seat == "seat_0" || o.Seat == "seat_1" || o.Seat == "seat_2"
	if !roleSeat && !biddingSeat {
		return fmt.Errorf("invalid seat %q", o.Seat)
	}
	if o.Phase != "" && o.Phase != "bidding" && o.Phase != "playing" && o.Phase != "finished" {
		return fmt.Errorf("invalid phase %q", o.Phase)
	}
	if o.Phase == "bidding" && !biddingSeat {
		return errors.New("bidding phase requires seat_0, seat_1, or seat_2")
	}
	if (o.Phase == "playing" || o.Phase == "finished") && !roleSeat {
		return fmt.Errorf("%s phase requires a landlord or farmer role", o.Phase)
	}
	if o.SeatIndex != nil && (*o.SeatIndex < 0 || *o.SeatIndex > 2) {
		return errors.New("seat_index must be between 0 and 2")
	}
	if len(o.LegalActions) == 0 {
		return errors.New("legal_actions must not be empty")
	}
	seen := map[int]bool{}
	for _, legal := range o.LegalActions {
		if seen[legal.ID] {
			return fmt.Errorf("duplicate legal action id %d", legal.ID)
		}
		seen[legal.ID] = true
	}
	return nil
}

func ValidateAction(o Observation, a Action) error {
	if err := ValidateObservation(o); err != nil {
		return err
	}
	if a.ProtocolVersion != Version {
		return fmt.Errorf("unsupported protocol_version %d", a.ProtocolVersion)
	}
	if a.GameID != o.GameID || a.TurnID != o.TurnID {
		return errors.New("action is not bound to the current game and turn")
	}
	if utf8.RuneCountInString(a.PublicComment) > 280 {
		return errors.New("public_comment exceeds 280 characters")
	}
	for _, legal := range o.LegalActions {
		if legal.ID == a.ActionID {
			return nil
		}
	}
	return fmt.Errorf("action_id %d is not legal", a.ActionID)
}

func NormalizeAction(o Observation, data []byte) (Action, error) {
	var a Action
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&a); err != nil {
		return Action{}, fmt.Errorf("decode action: %w", err)
	}
	if strings.TrimSpace(a.GameID) == "" {
		a.GameID = o.GameID
	}
	if strings.TrimSpace(a.TurnID) == "" {
		a.TurnID = o.TurnID
	}
	if a.ProtocolVersion == 0 {
		a.ProtocolVersion = Version
	}
	if err := ValidateAction(o, a); err != nil {
		return Action{}, err
	}
	return a, nil
}
