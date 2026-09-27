class Brewnicle < Formula
  desc "Terminal browser for recently added Homebrew packages"
  homepage "https://github.com/lmilojevicc/brewnicle"
  license "MIT"

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
