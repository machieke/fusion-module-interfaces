// A bounded artifact-installable client, not a native executor or tool proxy.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	omega "fusion.local/omega"
	"os"
)

func main() {
	config := flag.String("config", "", "private selected client configuration")
	action := flag.String("action", "", "head, create, get, allocate, metadata, submit, observe, capacity")
	deadline := flag.Int64("deadline-ms", 0, "fixed original absolute observation deadline; never renewed")
	identity := flag.String("identity", "", "explicit new intention or exact replay identity")
	session := flag.String("session", "", "accepted session UUID")
	text := flag.String("text", "", "explicit synthetic native input")
	template := flag.String("template", "shared", "operator-selected session template")
	assignment := flag.String("assignment", "synthetic-task", "selected input assignment")
	payload := flag.String("payload-file", "", "bounded generated payload file")
	reference := flag.String("ref-file", "", "previously captured immutable reference")
	content := flag.Bool("content", false, "request current authorized content disclosure")
	flag.Parse()
	var value interface{}
	cfg, e := omega.ReadConfig(*config)
	if e != nil {
		stop(e)
	}
	client, e := omega.New(cfg)
	if e != nil {
		stop(e)
	}
	switch *action {
	case "head":
		value, e = client.Head(*deadline)
	case "create":
		var data []byte
		data, e = os.ReadFile(*payload)
		if e == nil {
			value, e = client.Create(*identity, "application/json", data, *deadline)
		}
	case "get":
		var data []byte
		data, e = os.ReadFile(*reference)
		if e == nil {
			var r omega.Ref
			r, e = omega.ParseRef(data)
			if e == nil {
				var item omega.Envelope
				item, e = client.Get(r, *deadline)
				value = map[string]interface{}{"ref": item.Ref, "content_type": item.ContentType, "bytes_base64": item.Bytes}
			}
		}
	case "allocate":
		value, e = client.Session("allocate", omega.Object{"identity": *identity, "template": *template}, *deadline)
	case "metadata":
		value, e = client.Session("binding", omega.Object{"session": *session}, *deadline)
	case "submit":
		value, e = client.Session("submit", omega.Object{"session": *session, "identity": *identity, "text": *text, "assignment": *assignment}, *deadline)
	case "observe":
		value, e = client.Session("observe", omega.Object{"session": *session, "content": *content}, *deadline)
	case "capacity":
		value, e = client.Session("capacity", omega.Object{}, *deadline)
	default:
		e = fmt.Errorf("UNSUPPORTED_OPERATION")
	}
	if e != nil {
		stop(e)
	}
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetEscapeHTML(false)
	if e = encoder.Encode(value); e != nil {
		stop(e)
	}
}
func stop(e error) { fmt.Fprintln(os.Stderr, e.Error()); os.Exit(2) }
