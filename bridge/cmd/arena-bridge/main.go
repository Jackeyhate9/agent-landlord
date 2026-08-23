package main

import (
	"bufio"
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"

	"agent-landlord/bridge/adapter"
	"agent-landlord/bridge/client"
	"agent-landlord/bridge/identity"
	"agent-landlord/bridge/join"
)

func main() {
	if len(os.Args) < 3 || os.Args[1] != "join" {
		usage()
		os.Exit(2)
	}
	if err := runJoin(os.Args[2], os.Args[3:]); err != nil {
		fmt.Fprintln(os.Stderr, "arena-bridge:", err)
		os.Exit(1)
	}
}
func usage() {
	fmt.Fprintln(os.Stderr, "Usage: arena-bridge join <code> [--server URL] [--adapter codex|claude-code|ollama|openai-compatible|custom-http|custom-cli]")
	fmt.Fprintln(os.Stderr, "  arena-bridge join AL-X8F2-9DK7")
	fmt.Fprintln(os.Stderr, "  arena-bridge-windows.exe join AL-X8F2-9DK7 --server https://api.example.com")
}
func runJoin(code string, args []string) error {
	fs := flag.NewFlagSet("join", flag.ContinueOnError)
	server := fs.String("server", env("ARENA_URL", "http://localhost:8080"), "Arena HTTP base URL")
	kind := fs.String("adapter", "", "local adapter (if empty, interactive menu will appear)")
	httpURL := fs.String("http-url", os.Getenv("CUSTOM_AGENT_URL"), "Custom HTTP /act URL")
	cliCommand := fs.String("cli-command", os.Getenv("CUSTOM_AGENT_COMMAND"), "Custom CLI executable and arguments")
	ollamaURL := fs.String("ollama-url", env("OLLAMA_URL", "http://localhost:11434"), "Ollama URL")
	model := fs.String("model", os.Getenv("MODEL_NAME"), "local model name")
	if err := fs.Parse(args); err != nil {
		return err
	}
	// Interactive selection if no explicit adapter and no env-driven adapter
	adapterFlagSet := false
	fs.Visit(func(f *flag.Flag) { if f.Name == "adapter" { adapterFlagSet = true } })
	envAdapter := os.Getenv("AGENT_ADAPTER")
	if !adapterFlagSet && envAdapter != "" {
		*kind = envAdapter
		adapterFlagSet = true
	}
	if !adapterFlagSet {
		// No adapter specified -> show detection + menu as per spec
		fmt.Println("Detecting agents...")
		fmt.Println()
		dets := adapter.DetectCLIs()
		labelMap := map[string]string{"codex": "Codex", "claude": "Claude Code", "ollama": "Ollama"}
		for _, d := range dets {
			label := labelMap[d.Name]
			if label == "" {
				label = d.Name
			}
			if d.Available {
				fmt.Printf("✓ %s detected\n", label)
			} else {
				fmt.Printf("  %s not detected\n", label)
			}
		}
		fmt.Println()
		fmt.Println("Select Agent:")
		fmt.Println()
		options := []string{"Codex", "Claude Code", "Ollama", "OpenAI Compatible", "Custom HTTP", "Custom CLI"}
		for i, opt := range options {
			fmt.Printf("%d. %s\n", i+1, opt)
		}
		fmt.Println()
		fmt.Print("> ")
		reader := bufio.NewReader(os.Stdin)
		line, _ := reader.ReadString('\n')
		line = strings.TrimSpace(line)
		choice, _ := strconv.Atoi(line)
		if choice < 1 || choice > 6 {
			choice = 1
		}
		mapping := []string{"codex", "claude-code", "ollama", "openai-compatible", "custom-http", "custom-cli"}
		*kind = mapping[choice-1]
		// For ollama, prompt model if not set
		if *kind == "ollama" && *model == "" {
			fmt.Print("Model [qwen3:8b]: ")
			m, _ := reader.ReadString('\n')
			m = strings.TrimSpace(m)
			if m != "" {
				*model = m
			} else {
				*model = "qwen3:8b"
			}
		}
		if *kind == "custom-http" && *httpURL == "" {
			fmt.Print("Custom HTTP URL [http://localhost:9000/act]: ")
			u, _ := reader.ReadString('\n')
			u = strings.TrimSpace(u)
			if u != "" {
				*httpURL = u
			} else {
				*httpURL = "http://localhost:9000/act"
			}
		}
		if *kind == "custom-cli" && *cliCommand == "" {
			fmt.Print("Custom CLI command: ")
			c, _ := reader.ReadString('\n')
			c = strings.TrimSpace(c)
			*cliCommand = c
		}
		fmt.Println()
	} else if *kind == "" {
		*kind = "custom-http"
	}
	keyPath, err := identityPath()
	if err != nil {
		return err
	}
	id, err := identity.LoadOrCreate(keyPath)
	if err != nil {
		return err
	}
	signature, err := id.Sign([]byte(code))
	if err != nil {
		return err
	}
	// For non-interactive mode, also show detection once
	if adapterFlagSet {
		fmt.Println("Detecting agents...")
		fmt.Println()
		dets := adapter.DetectCLIs()
		labelMap := map[string]string{"codex": "Codex", "claude": "Claude Code", "ollama": "Ollama"}
		for _, d := range dets {
			label := labelMap[d.Name]
			if label == "" {
				label = d.Name
			}
			if d.Available {
				fmt.Printf("✓ %s detected\n", label)
			} else {
				fmt.Printf("  %s not detected\n", label)
			}
		}
		fmt.Println()
	}
	a, err := makeAdapter(*kind, *httpURL, *cliCommand, *ollamaURL, *model)
	if err != nil {
		return err
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	// 隐私友好的自动检测：只上报运行时类型名与模型名标签（不含路径/密钥/主机名）
	detRuntime, detModel, _ := adapter.DetectDefault()
	session, err := join.Exchange(ctx, *server, join.Request{
		ProtocolVersion: 1,
		JoinCode:        code,
		PublicKey:       id.PublicKey,
		Signature:       signature,
		Adapter:         a.Name(),
		DetectedRuntime: detRuntime,
		DetectedModel:   detModel,
	}, nil)
	if err != nil {
		return err
	}
	fmt.Printf("Connected as %s using %s. Session credentials remain in memory only.\n", session.AgentID, a.Name())
	runner := client.Runner{URL: session.WebSocketURL, SessionToken: session.SessionToken, ResumeID: session.ResumeID, Adapter: a, Heartbeat: 20 * time.Second}
	return runner.Run(ctx)
}
func makeAdapter(kind, httpURL, cliCommand, ollamaURL, model string) (adapter.Adapter, error) {
	switch kind {
	case "custom-http":
		if httpURL == "" {
			return nil, fmt.Errorf("--http-url or CUSTOM_AGENT_URL is required")
		}
		return &adapter.HTTPAdapter{URL: httpURL, BearerToken: os.Getenv("CUSTOM_AGENT_TOKEN")}, nil
	case "custom-cli":
		parts := strings.Fields(cliCommand)
		if len(parts) == 0 {
			return nil, fmt.Errorf("--cli-command or CUSTOM_AGENT_COMMAND is required")
		}
		// Explicitly inherit full environment so PATH/PATHEXT remain available on Windows
		return &adapter.CLIAdapter{Command: parts, Env: os.Environ()}, nil
	case "ollama":
		if model == "" {
			return nil, fmt.Errorf("--model or MODEL_NAME is required; query http://localhost:11434/api/tags")
		}
		return &adapter.OllamaAdapter{BaseURL: ollamaURL, Model: model}, nil
	case "openai-compatible":
		return &adapter.OpenAICompatibleAdapter{BaseURL: os.Getenv("MODEL_BASE_URL"), APIKey: os.Getenv("MODEL_API_KEY"), Model: model}, nil
	case "claude-code":
		return &adapter.ClaudeCLI{Model: model}, nil
	case "codex":
		// Codex uses same JSON schema as Claude Code; flags verified locally where possible, fallback to generic exec
		return &adapter.ClaudeCLI{Binary: "codex", Model: model}, nil
	default:
		return nil, fmt.Errorf("unknown adapter %q", kind)
	}
}
func identityPath() (string, error) {
	if p := os.Getenv("ARENA_BRIDGE_IDENTITY"); p != "" {
		clean := filepath.Clean(p)
		if strings.Contains(clean, "..") {
			return "", fmt.Errorf("ARENA_BRIDGE_IDENTITY must not contain ..")
		}
		if !filepath.IsAbs(clean) {
			return "", fmt.Errorf("ARENA_BRIDGE_IDENTITY must be an absolute path")
		}
		return clean, nil
	}
	dir, err := os.UserConfigDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(dir, "agent-landlord", "identity.json"), nil
}
func env(name, fallback string) string {
	if v := os.Getenv(name); v != "" {
		return v
	}
	return fallback
}
