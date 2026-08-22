package identity

import (
	"crypto/ed25519"
	"crypto/rand"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

type Identity struct {
	PublicKey  string `json:"public_key"`
	PrivateKey string `json:"private_key"`
}

func LoadOrCreate(path string) (Identity, error) {
	data, err := os.ReadFile(path)
	if err == nil {
		var id Identity
		if json.Unmarshal(data, &id) != nil || id.PublicKey == "" || id.PrivateKey == "" {
			return Identity{}, fmt.Errorf("invalid identity file %s", path)
		}
		return id, restrictFile(path)
	}
	if !os.IsNotExist(err) {
		return Identity{}, err
	}
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return Identity{}, err
	}
	id := Identity{PublicKey: base64.RawURLEncoding.EncodeToString(pub), PrivateKey: base64.RawURLEncoding.EncodeToString(priv)}
	data, _ = json.MarshalIndent(id, "", "  ")
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return Identity{}, err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, data, 0600); err != nil {
		return Identity{}, err
	}
	if err := restrictFile(tmp); err != nil {
		return Identity{}, err
	}
	if err := os.Rename(tmp, path); err != nil {
		return Identity{}, err
	}
	return id, restrictFile(path)
}

func (i Identity) Sign(message []byte) (string, error) {
	key, err := base64.RawURLEncoding.DecodeString(i.PrivateKey)
	if err != nil || len(key) != ed25519.PrivateKeySize {
		return "", fmt.Errorf("invalid private key")
	}
	return base64.RawURLEncoding.EncodeToString(ed25519.Sign(ed25519.PrivateKey(key), message)), nil
}
