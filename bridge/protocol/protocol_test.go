package protocol

import "testing"

func sampleObservation() Observation {
	return Observation{ProtocolVersion: 1, GameID: "game_1", TurnID: "turn_1", Seat: "landlord", Hand: []string{"3"}, LegalActions: []LegalAction{{ID: 0, Type: "pass"}, {ID: 18, Cards: []string{"3"}}}, DecisionTimeoutMS: 8000}
}

func TestValidateActionAcceptsLegalBoundAction(t *testing.T) {
	obs := sampleObservation()
	a := Action{ProtocolVersion: 1, GameID: obs.GameID, TurnID: obs.TurnID, ActionID: 18, PublicComment: "I will take the lead."}
	if err := ValidateAction(obs, a); err != nil {
		t.Fatalf("expected valid action: %v", err)
	}
}

func TestValidateActionRejectsWrongTurnOrUnknownAction(t *testing.T) {
	obs := sampleObservation()
	for _, a := range []Action{
		{ProtocolVersion: 1, GameID: obs.GameID, TurnID: "stale", ActionID: 18},
		{ProtocolVersion: 1, GameID: obs.GameID, TurnID: obs.TurnID, ActionID: 99},
		{ProtocolVersion: 2, GameID: obs.GameID, TurnID: obs.TurnID, ActionID: 18},
	} {
		if ValidateAction(obs, a) == nil {
			t.Fatalf("expected rejection for %#v", a)
		}
	}
}

func TestNormalizeActionBindsMinimalAdapterOutput(t *testing.T) {
	obs := sampleObservation()
	a, err := NormalizeAction(obs, []byte(`{"action_id":18,"public_comment":"public only"}`))
	if err != nil {
		t.Fatal(err)
	}
	if a.ProtocolVersion != 1 || a.GameID != obs.GameID || a.TurnID != obs.TurnID {
		t.Fatalf("not bound: %#v", a)
	}
}

func TestValidateObservationAcceptsTemporaryBiddingSeat(t *testing.T) {
	seatIndex := 1
	obs := sampleObservation()
	obs.Phase = "bidding"
	obs.Seat = "seat_1"
	obs.SeatIndex = &seatIndex
	obs.RemainingCardCounts = map[string]int{"seat_0": 17, "seat_1": 17, "seat_2": 17}
	if err := ValidateObservation(obs); err != nil {
		t.Fatalf("expected bidding observation to be valid: %v", err)
	}
}

func TestValidateObservationRejectsSeatFromWrongPhase(t *testing.T) {
	for _, tc := range []struct{ phase, seat string }{{"bidding", "landlord"}, {"playing", "seat_0"}} {
		obs := sampleObservation()
		obs.Phase, obs.Seat = tc.phase, tc.seat
		if ValidateObservation(obs) == nil {
			t.Fatalf("expected %s/%s to be rejected", tc.phase, tc.seat)
		}
	}
}
