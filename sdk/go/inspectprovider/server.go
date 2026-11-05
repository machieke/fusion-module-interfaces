package inspectprovider

import (
	"context"
	"crypto/tls"
	"encoding/json"
	omega "fusion.local/omega"
	"io"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
	"time"
)

func (o *Owner) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	reply := func(status int, v interface{}) { w.WriteHeader(status); json.NewEncoder(w).Encode(v) }
	failure := func(code string) {
		// Existing native transport parses typed contract errors at HTTP 200.
		status := 200
		reply(status, map[string]interface{}{"error": map[string]interface{}{"code": code, "retryable": code == "NOT_AVAILABLE" || code == "OVERLOADED"}})
	}
	if r.Method == "GET" && (r.URL.Path == "/healthz" || r.URL.Path == "/health/startup" || r.URL.Path == "/health/ready" || r.URL.Path == "/health/live") {
		o.mu.Lock()
		ready := !o.failed
		o.mu.Unlock()
		status := 200
		if !ready {
			status = 503
		}
		reply(status, map[string]interface{}{"ready": ready, "work_executed": false, "model_runtime": "FORBIDDEN"})
		return
	}
	if r.URL.Path == "/capacity" {
		if r.Method != "GET" || r.URL.RawQuery != "" || r.ContentLength != 0 || len(r.TransferEncoding) != 0 {
			failure("INVALID_ARGUMENT")
			return
		}
		auth := r.Header.Values("Authorization")
		if len(auth) != 1 || !strings.HasPrefix(auth[0], "Bearer ") {
			failure("UNAUTHORIZED")
			return
		}
		value, err := o.Capacity(auth[0][7:])
		if err != nil {
			failure(err.Error())
			return
		}
		reply(200, value)
		return
	}
	if r.Method == "GET" && r.URL.Path == "/descriptor" {
		if _, e := o.authenticate(strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer ")); e != nil {
			failure("UNAUTHORIZED")
			return
		}
		reply(200, Contract)
		return
	}
	if r.Method != "POST" || r.URL.Path != Contract["route"] || len(r.TransferEncoding) != 0 || r.ContentLength < 1 || r.ContentLength > omega.MaxWire {
		failure("INVALID_ARGUMENT")
		return
	}
	auth := r.Header.Values("Authorization")
	if len(auth) != 1 || !strings.HasPrefix(auth[0], "Bearer ") {
		failure("UNAUTHORIZED")
		return
	}
	b, e := io.ReadAll(io.LimitReader(r.Body, omega.MaxWire+1))
	if e != nil || int64(len(b)) != r.ContentLength {
		failure("INVALID_ARGUMENT")
		return
	}
	v, e := omega.Decode(b)
	if e != nil {
		failure("INVALID_ARGUMENT")
		return
	}
	q, e := obj(v)
	if e != nil {
		failure("INVALID_ARGUMENT")
		return
	}
	value, e := o.Invoke(auth[0][7:], q)
	if e != nil {
		code := e.Error()
		known := map[string]bool{"INVALID_ARGUMENT": true, "UNAUTHORIZED": true, "NOT_FOUND": true, "NOT_AVAILABLE": true, "CONFLICT": true, "OVERLOADED": true, "DEADLINE_EXCEEDED": true, "UNSUPPORTED_PROFILE": true, "UNSUPPORTED_OPERATION": true, "UNSUPPORTED_VERSION": true}
		if !known[code] {
			code = "NOT_AVAILABLE"
		}
		failure(code)
		return
	}
	reply(200, value)
}
func Run(config string) error {
	var cfg Config
	if e := decodeFile(config, &cfg); e != nil {
		return e
	}
	owner, e := Open(cfg)
	if e != nil {
		return e
	}
	defer owner.Close()
	certificate, e := tls.LoadX509KeyPair(cfg.Certificate, cfg.Key)
	if e != nil {
		return e
	}
	server := &http.Server{Addr: cfg.Listen, Handler: owner, ReadHeaderTimeout: 3 * time.Second, ReadTimeout: 5 * time.Second, WriteTimeout: 30 * time.Second, IdleTimeout: 10 * time.Second, MaxHeaderBytes: 16384, TLSConfig: &tls.Config{MinVersion: tls.VersionTLS12, Certificates: []tls.Certificate{certificate}}}
	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()
	done := make(chan struct{})
	go func() {
		defer close(done)
		timer := time.NewTicker(200 * time.Millisecond)
		defer timer.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-timer.C:
				owner.WorkOne()
			}
		}
	}()
	go func() {
		<-ctx.Done()
		stop, end := context.WithTimeout(context.Background(), 10*time.Second)
		defer end()
		server.Shutdown(stop)
	}()
	e = server.ListenAndServeTLS("", "")
	cancel()
	<-done
	if e == http.ErrServerClosed {
		return nil
	}
	return e
}
