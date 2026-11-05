package inspectprovider

// Capacity is an owner observation, not an execution operation. It neither
// consults dependencies nor saves state, reads a clock, dispatches or reserves.
import (
	"bytes"
	"encoding/json"
	omega "fusion.local/omega"
	"os"
	"strings"
)

const CapacityProfile = "go-inspect-capacity/1"
const RetainedResultLimit = 4096 // JSON-marshaled ref + durability receipt.

// completionProjection bounds every retained record after all pending jobs
// finish, including the independently committed result/outbox and final events.
// No persisted schema changes: reservations are derived from accepted immutable
// records and this build's explicit finite result limit. Old journals are not
// migrated; an old journal that exceeds the projection cannot admit new work.
func (o *Owner) completionProjection(add *Job) (int, error) {
	s := o.state
	s.LastMS = 1<<63 - 1
	s.Commit = int(^uint(0) >> 1)
	s.Jobs = make(map[string]*Job, len(o.state.Jobs)+1)
	for id, job := range o.state.Jobs {
		s.Jobs[id] = job
	}
	if add != nil {
		s.Jobs[add.ID] = add
	}
	padding := omega.Object{"padding": ""}
	b, _ := json.Marshal(padding)
	padding["padding"] = strings.Repeat("x", RetainedResultLimit-len(b))
	for id, job := range s.Jobs {
		if job.Delivered {
			continue
		}
		j := *job
		j.Attempts = 32
		j.Delivered = false // false occupies one more byte than true.
		j.Events = []string{"accepted", "result-committed", "completion-delivered"}
		if j.Result == nil && j.Error == "" {
			j.Result = padding
		}
		var result, errValue interface{}
		if j.Result != nil {
			result = j.Result
		}
		if j.Error != "" {
			errValue = j.Error
		}
		j.Outbox = omega.Object{"job_id": j.ID, "correlation_id": j.Request["correlation_id"], "causation_id": j.Request["message_id"], "result": result, "error": errValue}
		s.Jobs[id] = &j
	}
	b, e := json.Marshal(s)
	return len(b), e
}

func gauge(unit string, used, limit int) omega.Object {
	left := limit - used
	if left < 0 {
		left = 0
	}
	return omega.Object{"unit": unit, "used": number(int64(used)), "limit": number(int64(limit)), "headroom": number(int64(left))}
}

func (o *Owner) Capacity(token string) (omega.Object, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	principal, e := o.authenticate(token)
	if e != nil {
		return nil, e
	}
	// This is aggregate owner-scope accounting. No ordinary job permission
	// implies it; operators need a separately provisioned scoped credential.
	if e = o.authorize(principal, "execution.capacity", ""); e != nil {
		return nil, e
	}
	if o.failed {
		return nil, fail("NOT_AVAILABLE")
	}
	persisted, e := os.ReadFile(o.cfg.State)
	if e != nil {
		return nil, fail("NOT_AVAILABLE")
	}
	current, e := json.Marshal(o.state)
	if e != nil || !bytes.Equal(current, persisted) {
		return nil, fail("NOT_AVAILABLE")
	}
	projection, e := o.completionProjection(nil)
	if e != nil {
		return nil, fail("NOT_AVAILABLE")
	}
	pending, captured, delivered, errors, exhausted, spent, remaining := 0, 0, 0, 0, 0, 0, 0
	for _, j := range o.state.Jobs {
		spent += j.Attempts
		if j.Result != nil {
			captured++
		}
		if j.Error != "" {
			errors++
		}
		if j.Delivered {
			delivered++
		} else {
			pending++
			remaining += 32 - j.Attempts
			if j.Attempts == 32 {
				exhausted++
			}
		}
	}
	reserved := projection - len(current)
	if reserved < 0 {
		return nil, fail("NOT_AVAILABLE")
	}
	journal := gauge("bytes", len(current), omega.MaxWire)
	journal["completion_reserved"] = number(int64(reserved))
	journal["completion_projection"] = number(int64(projection))
	admission := omega.MaxWire - projection
	if admission < 0 {
		admission = 0
	}
	journal["admission_headroom"] = number(int64(admission))
	journal["reservation_kind"] = "admission-enforced-logical-worst-case"
	journal["completion_covered"] = projection <= omega.MaxWire
	journal["control_reserved"] = number(0)
	journal["control_policy"] = "read-observations-write-no-journal"
	result := omega.Object{
		"profile": CapacityProfile, "provider": Contract["selection"], "scope": o.cfg.Scope,
		"observation": "read-only-owner-snapshot", "work_executed": false,
		"revision": number(int64(o.state.Commit)), "last_commit_ms": number(o.state.LastMS),
		"jobs": gauge("jobs", len(o.state.Jobs), 128), "pending": gauge("jobs", pending, 4), "journal": journal,
		"worker_phases":     omega.Object{"unit": "worker-phases", "spent": number(int64(spent)), "remaining_for_pending": number(int64(remaining)), "per_job_limit": number(32), "reset": false},
		"closure":           omega.Object{"captured": number(int64(captured)), "delivered": number(int64(delivered)), "terminal_errors": number(int64(errors)), "exhausted_pending": number(int64(exhausted))},
		"input_limit_bytes": number(4096), "retained_result_limit_bytes": number(RetainedResultLimit),
		"unknown": omega.Object{"filesystem_free_bytes": nil, "pvc_capacity_bytes": nil, "rss_bytes": nil, "cpu_time_ns": nil, "next_request_bytes": nil, "observation_time_ms": nil, "reclaimable_bytes": nil},
	}
	if current, e := o.authenticate(token); e != nil || current != principal {
		return nil, fail("UNAUTHORIZED")
	}
	if e = o.authorize(principal, "execution.capacity", ""); e != nil {
		return nil, e
	}
	return result, nil
}
