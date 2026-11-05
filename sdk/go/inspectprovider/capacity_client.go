package inspectprovider

// Closed observation client: only GET /capacity, selected HTTPS endpoint, exact
// scope/provider/profile, an original caller deadline and no retries.
import (
	"context"
	"crypto/tls"
	"crypto/x509"
	omega "fusion.local/omega"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

type CapacityConfig struct {
	Profile  string   `json:"profile"`
	Scope    string   `json:"scope"`
	Provider string   `json:"provider"`
	Endpoint Endpoint `json:"endpoint"`
}

func checkCapacity(value omega.Object, scope string) error {
	if !exact(value, "profile", "provider", "scope", "observation", "work_executed", "revision", "last_commit_ms", "jobs", "pending", "journal", "worker_phases", "closure", "input_limit_bytes", "retained_result_limit_bytes", "unknown") ||
		value["profile"] != CapacityProfile || value["provider"] != Contract["selection"] || value["scope"] != scope || value["observation"] != "read-only-owner-snapshot" || value["work_executed"] != false ||
		value["input_limit_bytes"] != number(4096) || value["retained_result_limit_bytes"] != number(RetainedResultLimit) {
		return fail("NOT_AVAILABLE")
	}
	revision, err := integer(value["revision"])
	if err != nil || revision < 1 {
		return fail("NOT_AVAILABLE")
	}
	if _, err = integer(value["last_commit_ms"]); err != nil {
		return fail("NOT_AVAILABLE")
	}
	gauges := map[string]int64{"jobs": 128, "pending": 4, "journal": omega.MaxWire}
	counts := map[string]int64{}
	for key, limit := range gauges {
		g, e := obj(value[key])
		if e != nil {
			return fail("NOT_AVAILABLE")
		}
		fields := []string{"unit", "used", "limit", "headroom"}
		unit := "jobs"
		if key == "journal" {
			unit = "bytes"
			fields = append(fields, "completion_reserved", "completion_projection", "admission_headroom", "reservation_kind", "completion_covered", "control_reserved", "control_policy")
		}
		used, e := integer(g["used"])
		if e != nil || used > limit || !exact(g, fields...) || g["unit"] != unit || g["limit"] != number(limit) || g["headroom"] != number(limit-used) {
			return fail("NOT_AVAILABLE")
		}
		counts[key] = used
		if key == "journal" {
			projection, e := integer(g["completion_projection"])
			if e != nil || projection < used || projection > omega.MaxWire*2 {
				return fail("NOT_AVAILABLE")
			}
			left := limit - projection
			if left < 0 {
				left = 0
			}
			if g["completion_reserved"] != number(projection-used) || g["admission_headroom"] != number(left) || g["completion_covered"] != (projection <= limit) || g["reservation_kind"] != "admission-enforced-logical-worst-case" || g["control_reserved"] != number(0) || g["control_policy"] != "read-observations-write-no-journal" {
				return fail("NOT_AVAILABLE")
			}
		}
	}
	if counts["pending"] > counts["jobs"] {
		return fail("NOT_AVAILABLE")
	}
	w, e := obj(value["worker_phases"])
	if e != nil || !exact(w, "unit", "spent", "remaining_for_pending", "per_job_limit", "reset") || w["unit"] != "worker-phases" || w["per_job_limit"] != number(32) || w["reset"] != false {
		return fail("NOT_AVAILABLE")
	}
	spent, e := integer(w["spent"])
	if e != nil || spent > counts["jobs"]*32 {
		return fail("NOT_AVAILABLE")
	}
	remaining, e := integer(w["remaining_for_pending"])
	if e != nil || remaining > counts["pending"]*32 {
		return fail("NOT_AVAILABLE")
	}
	c, e := obj(value["closure"])
	if e != nil || !exact(c, "captured", "delivered", "terminal_errors", "exhausted_pending") {
		return fail("NOT_AVAILABLE")
	}
	closure := map[string]int64{}
	for key, v := range c {
		n, e := integer(v)
		if e != nil || n > counts["jobs"] {
			return fail("NOT_AVAILABLE")
		}
		closure[key] = n
	}
	if closure["captured"]+closure["terminal_errors"] > counts["jobs"] || closure["delivered"] != counts["jobs"]-counts["pending"] || closure["delivered"] > closure["captured"]+closure["terminal_errors"] || closure["exhausted_pending"] > counts["pending"] {
		return fail("NOT_AVAILABLE")
	}
	unknown, e := obj(value["unknown"])
	if e != nil || !exact(unknown, "filesystem_free_bytes", "pvc_capacity_bytes", "rss_bytes", "cpu_time_ns", "next_request_bytes", "observation_time_ms", "reclaimable_bytes") {
		return fail("NOT_AVAILABLE")
	}
	for _, v := range unknown {
		if v != nil {
			return fail("NOT_AVAILABLE")
		}
	}
	return nil
}

func ObserveCapacity(path string, deadline int64) (omega.Object, error) {
	var cfg CapacityConfig
	if e := decodeFile(path, &cfg); e != nil {
		return nil, fail("INVALID_ARGUMENT")
	}
	if cfg.Profile != "go-inspect-capacity-client/1" || cfg.Provider != Contract["selection"] || !labelPattern.MatchString(cfg.Scope) || !strings.HasPrefix(cfg.Scope, "synthetic-") {
		return nil, fail("UNSUPPORTED_PROFILE")
	}
	u, e := url.Parse(cfg.Endpoint.URL)
	if e != nil || u.Scheme != "https" || u.Host == "" || u.User != nil || u.RawQuery != "" || u.Fragment != "" || u.Path != "" {
		return nil, fail("UNAUTHORIZED")
	}
	if deadline <= time.Now().UnixMilli() {
		return nil, fail("DEADLINE_EXCEEDED")
	}
	pem, e := os.ReadFile(cfg.Endpoint.CAFile)
	if e != nil {
		return nil, fail("UNAUTHORIZED")
	}
	roots := x509.NewCertPool()
	if !roots.AppendCertsFromPEM(pem) {
		return nil, fail("UNAUTHORIZED")
	}
	credential, e := os.ReadFile(cfg.Endpoint.CredentialFile)
	if e != nil {
		return nil, fail("UNAUTHORIZED")
	}
	token := strings.TrimSpace(string(credential))
	if len(token) < 16 || strings.ContainsAny(token, "\r\n") {
		return nil, fail("UNAUTHORIZED")
	}
	ctx, cancel := context.WithDeadline(context.Background(), time.UnixMilli(deadline))
	defer cancel()
	request, e := http.NewRequestWithContext(ctx, "GET", cfg.Endpoint.URL+"/capacity", nil)
	if e != nil {
		return nil, e
	}
	request.Header.Set("Authorization", "Bearer "+token)
	transport := &http.Transport{TLSClientConfig: &tls.Config{RootCAs: roots, MinVersion: tls.VersionTLS12}, DisableKeepAlives: true}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, CheckRedirect: func(*http.Request, []*http.Request) error { return fail("UNAUTHORIZED") }}
	reply, e := client.Do(request)
	if e != nil {
		return nil, fail("NOT_AVAILABLE")
	}
	defer reply.Body.Close()
	data, e := io.ReadAll(io.LimitReader(reply.Body, omega.MaxWire+1))
	if e != nil || len(data) > omega.MaxWire || reply.StatusCode != 200 {
		return nil, fail("NOT_AVAILABLE")
	}
	v, e := omega.Decode(data)
	if e != nil {
		return nil, fail("NOT_AVAILABLE")
	}
	value, e := obj(v)
	if e != nil {
		return nil, e
	}
	if exact(value, "error") {
		detail, e := obj(value["error"])
		if e != nil || !exact(detail, "code", "retryable") {
			return nil, fail("NOT_AVAILABLE")
		}
		code, ok := detail["code"].(string)
		if !ok || (code != "UNAUTHORIZED" && code != "INVALID_ARGUMENT" && code != "NOT_AVAILABLE") || detail["retryable"] != (code == "NOT_AVAILABLE") {
			return nil, fail("NOT_AVAILABLE")
		}
		return nil, fail(code)
	}
	if e = checkCapacity(value, cfg.Scope); e != nil {
		return nil, e
	}
	return value, nil
}
