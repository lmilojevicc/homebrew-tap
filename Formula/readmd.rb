class Readmd < Formula
  desc "Terminal Markdown reader with wide-table support"
  homepage "https://github.com/lmilojevicc/readmd"
  url "https://github.com/lmilojevicc/readmd/archive/refs/tags/v0.1.1.tar.gz"
  sha256 "45832c7b20f3e8b67873e9e5e4ac6f95de0c4ac3f2ffef36534356aedbdd32a8"
  license "GPL-3.0-only"

  depends_on "go" => :build
  depends_on "python@3.14" => :test

  # Full texts absent from the modules, pinned to the SPDX License List v3.27.0 snapshot.
  resource "Apache-2.0" do
    url "https://raw.githubusercontent.com/spdx/license-list-data/d46e94e2c78ceede1cfc63cfa0396472d2798d4c/text/Apache-2.0.txt"
    sha256 "074e6e32c86a4c0ef8b3ed25b721ca23aca83df277cd88106ef7177c354615ff"
  end

  resource "Unicode-DFS-2016" do
    url "https://raw.githubusercontent.com/spdx/license-list-data/d46e94e2c78ceede1cfc63cfa0396472d2798d4c/text/Unicode-DFS-2016.txt"
    sha256 "1a33fc12a3abb0b3eb14db70e36ef1d0af51c93b1cc1f80f022c3bd406e9b874"
  end

  resource "Unicode-3.0" do
    url "https://raw.githubusercontent.com/spdx/license-list-data/d46e94e2c78ceede1cfc63cfa0396472d2798d4c/text/Unicode-3.0.txt"
    sha256 "f7db81051789b729fea528a63ec4c938fdcb93d9d61d97dc8cc2e9df6d47f2a1"
  end

  # Preserve data copyrights: uniseg uses Unicode 15; uax29 uses Unicode 17.
  resource "Unicode-15.0.0-NOTICE" do
    url "https://www.unicode.org/Public/15.0.0/ucd/ReadMe.txt"
    sha256 "53672c0d0b5185e3cf04c8e970d544c3af81ae7c8eeba0b9cf6d355aa954ae1f"
  end

  resource "Unicode-17.0.0-NOTICE" do
    url "https://www.unicode.org/Public/17.0.0/ucd/ReadMe.txt"
    sha256 "9fe1a90bd32659d7953616283dc2bffaa165518aae9ace026040c42c559ba606"
  end

  def install
    ENV["GOWORK"] = "off"
    ENV["GOTOOLCHAIN"] = "local"
    system "go", "mod", "download"
    system "go", "build", *std_go_args, "-mod=readonly", "-buildvcs=false", "."

    pkgshare.install "testdata/startup_pty.py", "THIRD_PARTY_NOTICES.md"

    # Restrict collection to go.mod's pinned modules, including other platforms.
    modules = JSON.parse(Utils.safe_popen_read("go", "mod", "edit", "-json")).fetch("Require")
    modules.each do |mod|
      directory = Utils.safe_popen_read("go", "list", "-m", "-f", "{{.Dir}}", mod.fetch("Path")).strip
      odie "Missing module directory for #{mod.fetch("Path")}" if directory.empty?
      source = Pathname(directory)
      destination = pkgshare/"licenses"/"#{mod.fetch("Path")}@#{mod.fetch("Version")}"
      notices = source.glob("**/*").select do |file|
        file.file? && file.basename.to_s.match?(/\A(?:LICEN[CS]E|COPYING|NOTICE|PATENTS)(?:[._-].*)?\z/i)
      end
      odie "No license notices found for #{mod.fetch("Path")}" if notices.empty?
      notices.each do |file|
        target = destination/file.relative_path_from(source)
        target.dirname.mkpath
        cp file, target
      end
    end

    (pkgshare/"licenses/go").mkpath
    cp Formula["go"].prefix/"LICENSE", pkgshare/"licenses/go/LICENSE"
    resources.each do |r|
      r.stage do
        (pkgshare/"licenses/supplemental").install File.basename(r.url) => "#{r.name}.txt"
      end
    end
  end

  test do
    system formula_opt_bin("python@3.14")/"python3.14", pkgshare/"startup_pty.py", bin/"readmd"
  end
end
