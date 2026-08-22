//go:build !windows

package identity

import "os"

func restrictFile(path string) error { return os.Chmod(path, 0600) }
