# pkg-go

Example Go package with no external dependencies. The module path
`example.com/pkg-go` is a placeholder; replace it before publication.

```go
package main

import (
    "fmt"
    pkggo "example.com/pkg-go"
)

func main() {
    fmt.Println(pkggo.Hello())
}
```

Run tests from this directory:

```sh
go test ./...
```
