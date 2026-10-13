package pkggo

import "testing"

func TestHello(t *testing.T) {
	if got := Hello(); got != "Hello from pkg-go!" {
		t.Errorf("Hello() = %q, want %q", got, "Hello from pkg-go!")
	}
}
