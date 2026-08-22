//go:build windows

package identity

import (
	"fmt"
	"os"
	"os/exec"
	"os/user"
)

// Windows has no POSIX mode bits. Apply the 0600 security equivalent: disable
// inherited ACLs and grant only the current account read/write access.
func restrictFile(path string) error {
	_ = os.Chmod(path, 0600)
	current, err := user.Current()
	if err != nil {
		return fmt.Errorf("resolve identity owner: %w", err)
	}
	output, err := exec.Command("icacls.exe", path, "/inheritance:r", "/grant:r", current.Username+":(R,W)").CombinedOutput()
	if err != nil {
		return fmt.Errorf("restrict identity ACL: %w: %s", err, output)
	}
	return nil
}
