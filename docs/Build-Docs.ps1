$ThisPath = Split-Path (Split-Path $PSCommandPath)
$PkgSrcPath = Join-Path $ThisPath -ChildPath "src/krillion_bot"
$GenDocPath = Join-Path $ThisPath -ChildPath "docs/generated"
pdoc --docformat "google" "$PkgSrcPath" -o "$GenDocPath" --mermaid