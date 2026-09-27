class Brewnicle < Formula
  desc "Terminal browser for recently added Homebrew packages"
  homepage "https://github.com/lmilojevicc/brewnicle"
  license "MIT"
  version "0.1.0"

  on_macos do
    on_arm do
      url "https://github.com/lmilojevicc/brewnicle/releases/download/v0.1.0/brewnicle_v0.1.0_darwin_arm64.tar.gz"
      sha256 "beea2350f7b5b63e3ca49615df22d2da141259533e8987e7d528b6212b6e926d"
    end
    on_intel do
      url "https://github.com/lmilojevicc/brewnicle/releases/download/v0.1.0/brewnicle_v0.1.0_darwin_amd64.tar.gz"
      sha256 "87e0932b5abce99867fb8eec5a9537e4150539f2ba2683fe149b150966c7ab30"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/lmilojevicc/brewnicle/releases/download/v0.1.0/brewnicle_v0.1.0_linux_arm64.tar.gz"
      sha256 "d8fde04af0cc56e9153f31c00ef5bf87a3221f937c1b673dd3ff06b786299863"
    end
    on_intel do
      url "https://github.com/lmilojevicc/brewnicle/releases/download/v0.1.0/brewnicle_v0.1.0_linux_amd64.tar.gz"
      sha256 "a9ac613ce7212e35c35940850135aca8520696dd513f1192622cdbb8e6ab3d02"
    end
  end


  head do
    url "https://github.com/lmilojevicc/brewnicle.git", branch: "main"
    depends_on "go" => :build
  end

  uses_from_macos "git"

  def install
    if build.head?
      ENV["GOWORK"] = "off"
      ENV["GOTOOLCHAIN"] = "local"
      ENV["CGO_ENABLED"] = "0"
      system "go", "mod", "download"
      system "go", "build", *std_go_args, "-mod=readonly", "-buildvcs=false", "./cmd/brewnicle"
      system "go", "run", "-mod=readonly", "./scripts/notices", "dependency-licenses"
      pkgshare.install "dependency-licenses" => "licenses"
    else
      bin.install "brewnicle"
      pkgshare.install "licenses"
    end
    pkgshare.install "LICENSE"
  end

  test do
    # Launching the TUI would start network indexing; no version flag exists.
    assert_predicate bin/"brewnicle", :executable?
    assert_path_exists pkgshare/"LICENSE"
    assert_path_exists pkgshare/"licenses/go/LICENSE"
    assert_path_exists pkgshare/"licenses/MODULES.txt"
  end
end
