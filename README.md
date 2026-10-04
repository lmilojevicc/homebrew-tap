# homebrew-tap
Homebrew tap for lmilojevicc's CLI tools (seshagy and more)

## defbrow

Searchable default-browser picker for macOS and Linux.

```sh
brew install lmilojevicc/tap/defbrow
```

Release binaries support Apple Silicon/ARM64 and Intel/AMD64. Requires macOS 12+
or Linux with glibc 2.39+. On Linux, install `xdg-utils` with your distribution's
package manager and run in your graphical desktop session.

## readmd

Terminal Markdown reader with wide-table support, built from source.

```sh
brew install lmilojevicc/tap/readmd
```

Or tap first, then install:

```sh
brew tap lmilojevicc/tap
brew install readmd
```

## brewnicle

Terminal browser for recently added Homebrew packages. Until the first stable
release is published and the formula is updated, install from the main branch:

```sh
brew install --HEAD lmilojevicc/tap/brewnicle
```

After that update, `brew install lmilojevicc/tap/brewnicle` installs a release
binary for macOS or Linux on Apple Silicon/ARM64 or Intel/AMD64.
