// Package headerguard validates HTTP metadata before Traefik calls an upstream.
// Traefik's native exact Header matcher remains the sole service selector.
package headerguard

import (
	"bufio"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"regexp"
)

// Config has no destinations, credentials, or caller-controlled routing map.
type Config struct {
	Static        bool `json:"static,omitempty"`
	RejectUnknown bool `json:"rejectUnknown,omitempty"`
}

// CreateConfig supplies Traefik's supported middleware defaults.
func CreateConfig() *Config { return &Config{} }

type guard struct {
	next   http.Handler
	config Config
}

// correlatedWriter sets the final response ID after upstream headers are copied.
// Native ResponseController unwrapping and explicit streaming interfaces preserve WS/H2.
type correlatedWriter struct {
	http.ResponseWriter
	id string
}

func (w *correlatedWriter) Header() http.Header {
	headers := w.ResponseWriter.Header()
	headers.Set("X-Request-ID", w.id)
	return headers
}

func (w *correlatedWriter) WriteHeader(status int) {
	w.Header()
	w.ResponseWriter.WriteHeader(status)
}

func (w *correlatedWriter) Unwrap() http.ResponseWriter { return w.ResponseWriter }

func (w *correlatedWriter) Flush() {
	w.Header()
	_ = http.NewResponseController(w.ResponseWriter).Flush()
}

func (w *correlatedWriter) Hijack() (net.Conn, *bufio.ReadWriter, error) {
	return http.NewResponseController(w.ResponseWriter).Hijack()
}

var identity = regexp.MustCompile(`^[A-Za-z][A-Za-z0-9]{0,63}$`)
var operation = regexp.MustCompile(`^/[a-z][A-Za-z0-9]*$`)
var correlation = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`)

// New constructs a synchronous metadata boundary, with no network calls.
func New(_ context.Context, next http.Handler, config *Config, _ string) (http.Handler, error) {
	if config == nil {
		return nil, fmt.Errorf("headerguard requires configuration")
	}
	return &guard{next: next, config: *config}, nil
}

func fail(w http.ResponseWriter, status int, code string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"ok": false, "result": nil, "error": code,
		"error_message": nil, "retry_after": nil,
	})
}

func (g *guard) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	ids := r.Header.Values("X-Request-ID")
	id := ""
	if len(ids) == 1 && correlation.MatchString(ids[0]) {
		id = ids[0]
	}
	if id == "" {
		data := make([]byte, 16)
		if _, err := rand.Read(data); err != nil {
			fail(w, http.StatusServiceUnavailable, "POKERLOST_REQUEST_ID_UNAVAILABLE")
			return
		}
		id = hex.EncodeToString(data)
	}
	r.Header.Set("X-Request-ID", id)
	w = &correlatedWriter{ResponseWriter: w, id: id}
	w.Header().Set("X-Request-ID", id)
	if r.Method == "OPTIONS" && r.Header.Get("Access-Control-Request-Method") != "" {
		fail(w, http.StatusForbidden, "POKERLOST_CROSS_ORIGIN_DISABLED")
		return
	}
	if g.config.Static && len(r.Header.Values("x-pokerlost-serviceId")) > 0 {
		fail(w, http.StatusNotFound, "POKERLOST_ROUTE_NOT_FOUND")
		return
	}
	if !g.config.Static {
		// Restrict public service paths; probes, metrics, legacy prefixes and encoded
		// paths cannot reach internal services, even with a valid service header.
		if !operation.MatchString(r.URL.Path) || r.URL.RawPath != "" ||
			r.URL.Path == "/metrics" || r.URL.Path == "/healthz" ||
			r.URL.Path == "/readyz" || r.URL.Path == "/livez" ||
			r.URL.Path == "/realtime" || r.URL.Path == "/ping" {
			fail(w, http.StatusNotFound, "POKERLOST_ROUTE_NOT_FOUND")
			return
		}
		values := r.Header.Values("x-pokerlost-serviceId")
		if len(values) == 0 {
			fail(w, http.StatusBadRequest, "POKERLOST_SERVICE_ID_REQUIRED")
			return
		}
		if len(values) != 1 || !identity.MatchString(values[0]) {
			fail(w, http.StatusBadRequest, "POKERLOST_SERVICE_ID_INVALID")
			return
		}
		if g.config.RejectUnknown {
			fail(w, http.StatusNotFound, "POKERLOST_SERVICE_ID_UNKNOWN")
			return
		}
	}
	g.next.ServeHTTP(w, r)
}
