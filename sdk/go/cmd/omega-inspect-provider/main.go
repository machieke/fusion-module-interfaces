// Independent stdlib provider; no Python/native interpreter or owner database.
package main

import (
	"flag"
	"fmt"
	"fusion.local/omega/inspectprovider"
	"os"
)

func main() {
	path := flag.String("config", "", "trusted local provider configuration; secrets are file references")
	flag.Parse()
	if *path == "" {
		fmt.Fprintln(os.Stderr, "configuration required")
		os.Exit(2)
	}
	if e := inspectprovider.Run(*path); e != nil {
		fmt.Fprintln(os.Stderr, "provider startup or shutdown failed")
		os.Exit(2)
	}
}
