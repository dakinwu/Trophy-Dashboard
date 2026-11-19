# Builds TrophyHunter.exe (project root) from launcher\TrophyHunter.cs.
# Uses the C# compiler bundled with Windows' .NET Framework 4.x - nothing to install.
# Usage (from anywhere):  powershell -ExecutionPolicy Bypass -File launcher\build.ps1
$ErrorActionPreference = 'Stop'

$here = $PSScriptRoot
$root = Split-Path $here -Parent
$source = Join-Path $here 'TrophyHunter.cs'
$icon = Join-Path $here 'trophy.ico'
$out = Join-Path $root 'TrophyHunter.exe'

$csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $csc)) {
    $csc = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
}
if (-not (Test-Path $csc)) {
    throw 'csc.exe (.NET Framework 4.x) not found. It ships with Windows 10/11; enable .NET Framework 4.8 in Windows Features.'
}

function New-TrophyIcon([string]$path) {
    # Draws the dashboard's trophy mark (gold cup on a dark rounded square) at
    # several sizes and stores each as a PNG frame inside one .ico file.
    Add-Type -AssemblyName System.Drawing
    $sizes = 256, 48, 32, 16
    $frames = @()
    foreach ($s in $sizes) {
        $bmp = New-Object System.Drawing.Bitmap $s, $s
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.SmoothingMode = 'AntiAlias'
        $g.Clear([System.Drawing.Color]::Transparent)
        $g.ScaleTransform($s / 48.0, $s / 48.0)   # draw in a 48x48 design grid

        $bg = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(0x15, 0x12, 0x0b))
        $r = 10
        $p = New-Object System.Drawing.Drawing2D.GraphicsPath
        $p.AddArc(0, 0, 2 * $r, 2 * $r, 180, 90)
        $p.AddArc(48 - 2 * $r, 0, 2 * $r, 2 * $r, 270, 90)
        $p.AddArc(48 - 2 * $r, 48 - 2 * $r, 2 * $r, 2 * $r, 0, 90)
        $p.AddArc(0, 48 - 2 * $r, 2 * $r, 2 * $r, 90, 90)
        $p.CloseFigure()
        $g.FillPath($bg, $p)

        $gold = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(0xF5, 0xB4, 0x00))
        $pen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(0xF5, 0xB4, 0x00)), 2.6
        $g.FillRectangle($gold, 13, 9, 22, 6)        # cup rim (overlaps bowl: no seam)
        $g.FillPie($gold, 13, 2, 22, 24, 0, 180)     # cup bowl (lower half-ellipse)
        $g.DrawArc($pen, 7.5, 11, 10, 10, 90, 180)   # left handle
        $g.DrawArc($pen, 30.5, 11, 10, 10, 270, 180) # right handle
        $g.FillRectangle($gold, 22, 25, 4, 6)        # stem
        $g.FillRectangle($gold, 17, 31, 14, 3)       # neck
        $g.FillRectangle($gold, 14, 34, 20, 4)       # base

        $ms = New-Object System.IO.MemoryStream
        $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
        $frames += , @{ Size = $s; Bytes = $ms.ToArray() }
        $g.Dispose(); $bmp.Dispose(); $ms.Dispose()
    }

    $fs = [System.IO.File]::Create($path)
    $w = New-Object System.IO.BinaryWriter $fs
    $w.Write([UInt16]0); $w.Write([UInt16]1); $w.Write([UInt16]$frames.Count)
    $offset = 6 + 16 * $frames.Count
    foreach ($f in $frames) {
        $dim = if ($f.Size -ge 256) { 0 } else { $f.Size }
        $w.Write([byte]$dim); $w.Write([byte]$dim)
        $w.Write([byte]0); $w.Write([byte]0)
        $w.Write([UInt16]1); $w.Write([UInt16]32)
        $w.Write([UInt32]$f.Bytes.Length); $w.Write([UInt32]$offset)
        $offset += $f.Bytes.Length
    }
    foreach ($f in $frames) { $w.Write($f.Bytes) }
    $w.Dispose(); $fs.Dispose()
}

if (-not (Test-Path $icon)) {
    Write-Host 'Generating launcher\trophy.ico ...'
    New-TrophyIcon $icon
}

& $csc /nologo /target:winexe /optimize+ /platform:anycpu `
    "/win32icon:$icon" "/out:$out" `
    /reference:System.Windows.Forms.dll $source
if ($LASTEXITCODE -ne 0) { throw "csc.exe failed with exit code $LASTEXITCODE" }

Write-Host "Built $out"
