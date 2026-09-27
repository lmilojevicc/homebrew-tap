# homebrew-tap
Homebrew tap for lmilojevicc's CLI tools (seshagy and more)

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
