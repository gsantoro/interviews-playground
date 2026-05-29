# README

## Links
- [PR](https://github.com/snyk/code-review-exercise-golang/pull/17)
- [Issue](https://github.com/snyk/code-review-exercise-golang/issues/11)
- [Conventional Comments](https://conventionalcomments.org/)

## Interview notes
- No live coding required
- Collaborative exercise (aka code review / pair programming)

## Issue description

> a full list of all transitive dependencies for a given package

> Snyk scans NodeJS packages to identify and assist developers in remediating vulnerabilities prior to merging their code back with its project

> Some packages to look out for are:
    express
    npm
    trucolor
    @snyk/snyk-docker-pull

> A user may provide invalid input (e.g. a non-existing package), causing the web-server to crash if there is no error handling in place.




## Code notes
- Handler
    - PackageVersion
        - calls: resolver.ResolvePackage(constraint, npmPkg)
        - encode response as JSON

- Resolver:
    - constructor: npm.NewClient as PackageFetcher (FetchPackage, FetchPackageMeta)
        - http client with a registryURL 
    - implements: ResolvePackage
        - calls: FetchPackageMeta
        - calls: ResolveHighestVersion
            - if a version respect the constraint I get the highest version in that range
        - calls: FetchPackage
        - calls: NewConstrant + ResolvePackage for each dependency
- PackageFetcher (implemented by client.go for NPM)
    - implements: FetchPackage
    - implements: FetchPackageMeta
        - get all the versions for a package by name

- NpmPackageVersion
    - name
    - version
    - dependencies map[string]*NpmPackageVersion
- Package
    - name
    - version
    - dependencies map[string]string
- PackageMeta

Random Notes:
- server.go
    - nice to separate code from npm since it applies to other fetchers



## ToDo
- [ ] check for those npm packages provided in the issue
- [ ] check for non-existing package. how does it behave? avoid crashing
- [ ] IMPORTANT: async fetching
- [ ] check json output format
- [ ] how to handle errors





- [ ] checks tests
    - [ ] test coverage
    - [ ] are we checking everything
- [ ] scan with Snyk (code coverage, CVEs)
- [ ] improve dockerfile??
- [ ] remove `//nolint:gosec // #nosec G402`
- [ ] use a constraint for params??
- [ ] simplify: fetchpackage and fetchPackagemeta as a single request?


## Done:
1. `snyk test` = no vulnerabilities
2. `snyk code test`

```
➜ snyk code test

Testing /Users/gsantoro/workspace/interviews/2025/snyk/code-review-exercise-golang ...

 ✗ [Low] Path Traversal
   Path: test/integration/helper_test.go, line 21
   Info: Unsanitized input from the request URL flows into os.ReadFile, where it is used as a path. This may result in a Path Traversal vulnerability and allow an attacker to read arbitrary files.

 ✗ [Low] Cross-site Scripting (XSS)
   Path: test/integration/helper_test.go, line 28
   Info: Unsanitized input from the request URL flows into Write, where it is used to render an HTML page returned to the user. This may result in a Reflected Cross-Site Scripting attack (XSS).


✔ Test completed

Organization:      giuseppe.santoro
Test type:         Static code analysis
Project path:      /Users/gsantoro/workspace/interviews/2025/snyk/code-review-exercise-golang

Summary:

  2 Code issues found
  2 [Low]
```


3. `snyk container test npmjs-deps-fetcher`

