class Defbrow < Formula
  desc "Searchable default-browser picker for macOS and Linux"
  homepage "https://github.com/lmilojevicc/defbrow"
  license "MIT"

  on_macos do
    depends_on macos: :monterey
    on_arm do
      url "https://github.com/lmilojevicc/defbrow/releases/download/v0.1.0/defbrow_0.1.0_darwin_arm64.tar.gz"
      sha256 "9f9d3098b8533eaf1cc00130651d63f4f6047ed0d62abc5215c16bf50d5b254d"
    end
    on_intel do
      url "https://github.com/lmilojevicc/defbrow/releases/download/v0.1.0/defbrow_0.1.0_darwin_amd64.tar.gz"
      sha256 "f3194e04e34adf6f4a0558fd397cefc22f2d4f3cf2479fb2b92d7bc05364e3f1"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/lmilojevicc/defbrow/releases/download/v0.1.0/defbrow_0.1.0_linux_arm64.tar.gz"
      sha256 "33dbd134a14c10375da296466ee2c8df5f94673641e6dd6aa41b98fecda63009"
    end
    on_intel do
      url "https://github.com/lmilojevicc/defbrow/releases/download/v0.1.0/defbrow_0.1.0_linux_amd64.tar.gz"
      sha256 "3ed12998b4ea6acccad32186b20cde751cc22ebe17d957a45de035e9572a866e"
    end
  end

  def install
    bin.install "defbrow"
    doc.install "LICENSE", "THIRD_PARTY_NOTICES.txt", "docs/usage.md"
  end

  def caveats
    <<~EOS
      On Linux, install xdg-utils with your distribution package manager
      and use a graphical desktop session as your normal user.
      The Linux binaries require glibc 2.39 or newer (Ubuntu 24.04+).
      On macOS, changing defaults may require OS consent.
    EOS
  end

  test do
    assert_match "Usage:", shell_output("#{bin}/defbrow --help")
    assert_equal "defbrow #{version}", shell_output("#{bin}/defbrow --version").strip
  end
end
