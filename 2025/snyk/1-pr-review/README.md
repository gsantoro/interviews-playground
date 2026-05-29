# README

## Links
- [PR](https://github.com/snyk/code-review-exercise-golang/pull/17)
- [Issue](https://github.com/snyk/code-review-exercise-golang/issues/11)
- [Conventional Comments](https://conventionalcomments.org/)

## Notes

### 1. issue (blocking): Linting errors - line 71 @ internal/npm/resolver.go
// issue (blocking): `func Resolver.resolvePackageHighestVersion is unused` => delete this method entirely
// The CICD checks for the PR caught the same error. I caught this error when running `make fmt` or `make lint`
// 
// Solution: removing the method entirely makes the code simpler. 
// 
// Notes: It was useful before since we called this method twice but now it would have been called only once. So inlining it is better solution.
// 
// After fix: run again `make lint` and `make fmt` locally to check the error is gone

---

Fixed at `feat/gsantoro-fix` at commit `7d6562082b31c1fb5e3e404d6147b48bbb35b248` (#1)

More info:

```bash
make lint
```

returns

```bash
INFO [runner] linters took 3.804279458s with stages: goanalysis_metalinter: 3.80376925s
internal/npm/resolver.go:71:19: func `Resolver.resolvePackageHighestVersion` is unused (unused)
func (r Resolver) resolvePackageHighestVersion(ctx context.Context, name string, constraint *semver.Constraints) (string, error) {
                  ^
```


### 2. issue (blocking): Failing integration test - line 44 @ test/integration/testdata/expect_react_16.13.0.json
// issue (blocking): failing integration test => replace the expected version for prop-types in the attached json file from 15.7.2 to 15.8.1
// Expected version of prop-types was manually changed in this PR from 15.8.1 to 15.7.2. This error was caught by the CI/CD tests but it can be manually checked with `make test-int` after running `make run` in a separate shell to run the web server.
// 
// Solution: change the expected version of the prop-types library in the file `test/integration/testdata/expect_react_16.13.0.json`
// 
// After fix: run again `make test-int` locally (while still running the web server with `make run` in a separate shell) to check the error is gone.


---

Fixed at `feat/gsantoro-fix` at commit `e0f6c30ae0d39030618945cee5b6304f86ea11a5` (#2)

More info:

```bash
➜ make test-int

* Executing target: test-int
mkdir -p test/results
go tool gotestsum --junitfile test/results/integration-tests.xml -- -count=1 -tags integration -v ./test/...
✖  test/integration (1.432s)

=== Failed
=== FAIL: test/integration TestPackageNameVersionEndpoint (1.14s)
    api_test.go:74:
                Error Trace:    /Users/gsantoro/workspace/interviews/2025/snyk/1-pr-review/code-review-exercise-golang/test/integration/api_test.go:74
                Error:          Not equal:
                                expected: "{\n  \"dependencies\": {\n    \"loose-envify\": {\n      \"dependencies\": {\n        \"js-tokens\": {\n          \"dependencies\": {},\n          \"name\": \"js-tokens\",\n          \"version\": \"4.0.0\"\n        }\n      },\n      \"name\": \"loose-envify\",\n      \"version\": \"1.4.0\"\n    },\n    \"object-assign\": {\n      \"dependencies\": {},\n      \"name\": \"object-assign\",\n      \"version\": \"4.1.1\"\n    },\n    \"prop-types\": {\n      \"dependencies\": {\n        \"loose-envify\": {\n          \"dependencies\": {\n            \"js-tokens\": {\n              \"dependencies\": {},\n              \"name\": \"js-tokens\",\n              \"version\": \"4.0.0\"\n            }\n          },\n          \"name\": \"loose-envify\",\n          \"version\": \"1.4.0\"\n        },\n        \"object-assign\": {\n          \"dependencies\": {},\n          \"name\": \"object-assign\",\n          \"version\": \"4.1.1\"\n        },\n        \"react-is\": {\n          \"dependencies\": {},\n          \"name\": \"react-is\",\n          \"version\": \"16.13.1\"\n        }\n      },\n      \"name\": \"prop-types\",\n      \"version\": \"15.7.2\"\n    }\n  },\n  \"name\": \"react\",\n  \"version\": \"16.13.0\"\n}"
                                actual  : "{\n  \"dependencies\": {\n    \"loose-envify\": {\n      \"dependencies\": {\n        \"js-tokens\": {\n          \"dependencies\": {},\n          \"name\": \"js-tokens\",\n          \"version\": \"4.0.0\"\n        }\n      },\n      \"name\": \"loose-envify\",\n      \"version\": \"1.4.0\"\n    },\n    \"object-assign\": {\n      \"dependencies\": {},\n      \"name\": \"object-assign\",\n      \"version\": \"4.1.1\"\n    },\n    \"prop-types\": {\n      \"dependencies\": {\n        \"loose-envify\": {\n          \"dependencies\": {\n            \"js-tokens\": {\n              \"dependencies\": {},\n              \"name\": \"js-tokens\",\n              \"version\": \"4.0.0\"\n            }\n          },\n          \"name\": \"loose-envify\",\n          \"version\": \"1.4.0\"\n        },\n        \"object-assign\": {\n          \"dependencies\": {},\n          \"name\": \"object-assign\",\n          \"version\": \"4.1.1\"\n        },\n        \"react-is\": {\n          \"dependencies\": {},\n          \"name\": \"react-is\",\n          \"version\": \"16.13.1\"\n        }\n      },\n      \"name\": \"prop-types\",\n      \"version\": \"15.8.1\"\n    }\n  },\n  \"name\": \"react\",\n  \"version\": \"16.13.0\"\n}"

                                Diff:
                                --- Expected
                                +++ Actual
                                @@ -43,3 +43,3 @@
                                       "name": "prop-types",
                                -      "version": "15.7.2"
                                +      "version": "15.8.1"
                                     }
                Test:           TestPackageNameVersionEndpoint

DONE 2 tests, 1 failure in 1.909s
make: *** [test-int] Error 1
```


### 3. suggestion (blocking): Fix error handling for indirect dependencies - line 65 @ internal/npm/resolver.go
// suggestion (blocking): we should be returning an error if you cannot resolve an indirect package instead of failing silently
// We should remove the linter comment `//nolint:errcheck // best effort` and instead corrently handle the case when an indirect package cannot be resolved.
// 
// Solution: if you want to keep the changes mimimal you could just handle the `ResolvePackage` errors otherwise we should refactor the use of NpmPackageVersion
// 
// After fix: run again `make lint` to make there is no linting error after removing the linter warning suppression comment.

---

Fixed at `feat/gsantoro-fix` at commit `e0f6c30ae0d39030618945cee5b6304f86ea11a5` (#2)

### 4. question (non-blocking): Restore removed test `fetch meta failure for dependency package` - line 93 @ internal/npm/resolver_test.go
// question (non-blocking): why did you remove this test? it still works
// I don't see any reason to remove this test. 
// 
// Solution: Bring back the test
// 
// After fix: run again `make test` to make there is no testing error after reintroducing this test.

---

Fixed at `feat/gsantoro-fix` at commit `9df6c75773f72bdb5ab4fb0e400cb161a2871249` (#4)

### 5. praise (non-blocking): Praise for improved testing - line 139 @ internal/npm/resolver_test.go
// praise (non-blocking): great job at testing for indirect package resolution when successfull

---

## Other improvements @ feat/gsantoro-fix

### suggestion (non-blocking): use cache
Refactor at `feat/gsantoro-fix` at commit `39b2a2dd31333fe28c21586944f4a575f869dc0c` (#5)
- Use cache on disk for FetchPackage and FetchPackageMeta
- added another param/config for npm.cache
- disable cache when running in Docker
- no cache by default to avoid using with integration tests
- added logger to NpmClient
- use noop logger `discardLogger` for unit tests

 and `4e354da9266df60d02317071ba5824a735763021` (#6)
- invalidate cache that is older than 1 day
- use cache in docker image

### suggestion (non-blocking): remove NpmPackageVersion
Refactor at `feat/gsantoro-fix` at commit `e0f6c30ae0d39030618945cee5b6304f86ea11a5` (#2):
- moved ErrPackageNotFound from package `npm` to `handler` since it can be shared with multiple resolver
- removed nolint `//nolint:errcheck // best effort` to have better error handling instead of having a best effor solution
- reverted back change for `ResolvePackage`
    - it takes a `pkgName` and return (`*handler.Package`, error) ==> better than passing an object that is modified. simpler interface
    - `handler.Package` instead of `npm.NpmPackageVersion` -> has `omitempty` for `dependencies` so the returned json is shorter (no need for `"dependencies": {}`). I had to change `handler_test.go` and `expect_react_16.13.0.json` and run `make gen` to update the mocks
    - `handler.Package` can be shared between resolvers. It is used by `npm` package only for the return values. The implementation of npm.Package and npm.PackageMeta can stays as it is since those are internal structs and not shared with `handler` package.
    - avoid allocating an empty `Dependencies` map when calling ResolvePackage if the only thing that methods needs is a packageName


## suggestion (non-blocking): Docker build with Go version
Refactor at `feat/gsantoro-fix` at commit `1d4829e3a113235fd0ff4889567e4345c2ce5fce` (#3):
- `make docker-build` should pass the current version of golang to the docker build command like `--build-arg GO_VERSION=$$(cat .go-version)` so that the golang binary is compiled with the same golang version as in the code.



## suggestion (non-blocking): Snyk scan
1. `snyk test` = no vulnerabilities
2. `snyk code test`

```
➜ snyk code test

Testing /Users/gsantoro/workspace/interviews/2025/snyk/1-pr-review/gsantoro-fix ...

 ✗ [Low] Path Traversal
   Path: test/integration/helper_test.go, line 21
   Info: Unsanitized input from the request URL flows into os.ReadFile, where it is used as a path. This may result in a Path Traversal vulnerability and allow an attacker to read arbitrary files.

 ✗ [Low] Cross-site Scripting (XSS)
   Path: test/integration/helper_test.go, line 28
   Info: Unsanitized input from the request URL flows into Write, where it is used to render an HTML page returned to the user. This may result in a Reflected Cross-Site Scripting attack (XSS).


✔ Test completed

Organization:      giuseppe.santoro
Test type:         Static code analysis
Project path:      /Users/gsantoro/workspace/interviews/2025/snyk/1-pr-review/gsantoro-fix

Summary:

  2 Code issues found
  2 [Low]
```


3. `snyk container test npmjs-deps-fetcher:dev --severity-threshold=medium --file=Dockerfile`

Didn't work out of the box since the image is not available on a docker registry

I tried 

```bash
IMAGE_ID=$(docker images npmjs-deps-fetcher:dev --format "{{.ID}}")
snyk container test $IMAGE_ID --severity-threshold=medium --file=Dockerfile
```

but got

```bash

 ERROR   Unspecified Error (SNYK-CLI-0000)

           Failed to scan image "43f4590734d1". Please make sure the image and/or
           repository exist, and that you are using the correct credentials.
```