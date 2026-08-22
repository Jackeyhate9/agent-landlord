package identity

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestLoadOrCreatePersistsOnePrivateKeyWithRestrictedPermissions(t *testing.T) {
	path := filepath.Join(t.TempDir(), "identity.json")
	a, err := LoadOrCreate(path)
	if err != nil {
		t.Fatal(err)
	}
	b, err := LoadOrCreate(path)
	if err != nil {
		t.Fatal(err)
	}
	if a.PublicKey != b.PublicKey {
		t.Fatal("identity changed")
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatal(err)
	}
	// Windows does not expose DACLs through FileMode; identity_windows.go
	// applies an owner-only DACL with icacls instead.
	if runtime.GOOS != "windows" && info.Mode().Perm()&0077 != 0 {
		t.Fatalf("key file is too permissive: %o", info.Mode().Perm())
	}
}
