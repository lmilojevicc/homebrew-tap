class Brewnicle < Formula
  desc "Terminal browser for recently added Homebrew packages"
  homepage "https://github.com/lmilojevicc/brewnicle"
  license "MIT"
  version "0.2.0"

  on_macos do
    on_arm do
      url "https://github.com/lmilojevicc/brewnicle/releases/download/v0.2.0/brewnicle_v0.2.0_darwin_arm64.tar.gz"
      sha256 "5247ebb13d5558c7ff6d96d828c962516bbbe99f05897ef1ec3c398e083e579e"
    end
    on_intel do
      url "https://github.com/lmilojevicc/brewnicle/releases/download/v0.2.0/brewnicle_v0.2.0_darwin_amd64.tar.gz"
      sha256 "6d06f1d807e5b340fa2ef77bcabfc0b08fe792eb56aff83862951f3a3e99fd9a"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/lmilojevicc/brewnicle/releases/download/v0.2.0/brewnicle_v0.2.0_linux_arm64.tar.gz"
      sha256 "388fe728a78b5a9788f94b686c30b1af65f23a1b0d5438fc0b4388a9fb827f75"
    end
    on_intel do
      url "https://github.com/lmilojevicc/brewnicle/releases/download/v0.2.0/brewnicle_v0.2.0_linux_amd64.tar.gz"
      sha256 "ac2d0fdaa43f7957ed5fe7539497e6c8eb5744d59dc497c2a3051e943b78685b"
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
