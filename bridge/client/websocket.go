package client

import (
	"bufio"
	"context"
	"crypto/rand"
	"crypto/sha1"
	"crypto/tls"
	"encoding/base64"
	"encoding/binary"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

type webSocket struct {
	conn net.Conn
	r    *bufio.Reader
	mu   sync.Mutex
}

func DialWebSocket(ctx context.Context, rawURL, token string) (Socket, error) {
	u, err := url.Parse(rawURL)
	if err != nil {
		return nil, err
	}
	if u.Scheme != "ws" && u.Scheme != "wss" {
		return nil, fmt.Errorf("WebSocket URL must use ws or wss")
	}
	host := u.Host
	if !strings.Contains(host, ":") {
		if u.Scheme == "wss" {
			host += ":443"
		} else {
			host += ":80"
		}
	}
	d := net.Dialer{}
	var conn net.Conn
	if u.Scheme == "wss" {
		conn, err = tls.DialWithDialer(&d, "tcp", host, &tls.Config{ServerName: u.Hostname(), MinVersion: tls.VersionTLS12})
	} else {
		conn, err = d.DialContext(ctx, "tcp", host)
	}
	if err != nil {
		return nil, err
	}
	keyBytes := make([]byte, 16)
	if _, err = rand.Read(keyBytes); err != nil {
		conn.Close()
		return nil, err
	}
	key := base64.StdEncoding.EncodeToString(keyBytes)
	path := u.RequestURI()
	if path == "" {
		path = "/"
	}
	headers := fmt.Sprintf("GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n", path, u.Host, key)
	if token != "" {
		headers += "Authorization: Bearer " + token + "\r\n"
	}
	headers += "\r\n"
	if _, err = io.WriteString(conn, headers); err != nil {
		conn.Close()
		return nil, err
	}
	reader := bufio.NewReader(conn)
	req := &http.Request{Method: http.MethodGet}
	res, err := http.ReadResponse(reader, req)
	if err != nil {
		conn.Close()
		return nil, err
	}
	defer res.Body.Close()
	if res.StatusCode != http.StatusSwitchingProtocols {
		conn.Close()
		return nil, fmt.Errorf("WebSocket upgrade status %s", res.Status)
	}
	sum := sha1.Sum([]byte(key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"))
	want := base64.StdEncoding.EncodeToString(sum[:])
	if res.Header.Get("Sec-WebSocket-Accept") != want {
		conn.Close()
		return nil, fmt.Errorf("invalid WebSocket accept")
	}
	return &webSocket{conn: conn, r: reader}, nil
}
func (w *webSocket) Close() error                              { return w.conn.Close() }
func (w *webSocket) Ping(ctx context.Context) error            { return w.writeFrame(ctx, 0x9, nil) }
func (w *webSocket) Write(ctx context.Context, b []byte) error { return w.writeFrame(ctx, 0x1, b) }
func (w *webSocket) writeFrame(ctx context.Context, opcode byte, payload []byte) error {
	w.mu.Lock()
	defer w.mu.Unlock()
	if deadline, ok := ctx.Deadline(); ok {
		_ = w.conn.SetWriteDeadline(deadline)
	} else {
		_ = w.conn.SetWriteDeadline(time.Time{})
	}
	mask := make([]byte, 4)
	if _, err := rand.Read(mask); err != nil {
		return err
	}
	header := []byte{0x80 | opcode}
	n := len(payload)
	switch {
	case n < 126:
		header = append(header, 0x80|byte(n))
	case n <= 65535:
		header = append(header, 0x80|126, byte(n>>8), byte(n))
	default:
		header = append(header, 0x80|127)
		var size [8]byte
		binary.BigEndian.PutUint64(size[:], uint64(n))
		header = append(header, size[:]...)
	}
	header = append(header, mask...)
	masked := make([]byte, n)
	for i := range payload {
		masked[i] = payload[i] ^ mask[i%4]
	}
	if _, err := w.conn.Write(header); err != nil {
		return err
	}
	_, err := w.conn.Write(masked)
	return err
}
func (w *webSocket) Read(ctx context.Context) ([]byte, error) {
	for {
		if deadline, ok := ctx.Deadline(); ok {
			_ = w.conn.SetReadDeadline(deadline)
		} else {
			_ = w.conn.SetReadDeadline(time.Time{})
		}
		first, err := w.r.ReadByte()
		if err != nil {
			return nil, err
		}
		second, err := w.r.ReadByte()
		if err != nil {
			return nil, err
		}
		if first&0x80 == 0 {
			return nil, fmt.Errorf("fragmented frames unsupported")
		}
		opcode := first & 0x0f
		masked := second&0x80 != 0
		length := uint64(second & 0x7f)
		if length == 126 {
			var b [2]byte
			if _, err = io.ReadFull(w.r, b[:]); err != nil {
				return nil, err
			}
			length = uint64(binary.BigEndian.Uint16(b[:]))
		} else if length == 127 {
			var b [8]byte
			if _, err = io.ReadFull(w.r, b[:]); err != nil {
				return nil, err
			}
			length = binary.BigEndian.Uint64(b[:])
		}
		if length > 1<<20 {
			return nil, fmt.Errorf("WebSocket message exceeds 1 MiB")
		}
		var mask [4]byte
		if masked {
			if _, err = io.ReadFull(w.r, mask[:]); err != nil {
				return nil, err
			}
		}
		payload := make([]byte, int(length))
		if _, err = io.ReadFull(w.r, payload); err != nil {
			return nil, err
		}
		if masked {
			for i := range payload {
				payload[i] ^= mask[i%4]
			}
		}
		switch opcode {
		case 0x1:
			return payload, nil
		case 0x8:
			return nil, io.EOF
		case 0x9:
			if err = w.writeFrame(ctx, 0xA, payload); err != nil {
				return nil, err
			}
		case 0xA:
			continue
		default:
			return nil, fmt.Errorf("unsupported WebSocket opcode %d", opcode)
		}
	}
}
