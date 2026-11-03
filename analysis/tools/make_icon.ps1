# Gera o ícone original do app (planeta com anel e estrela) em app/src/main/res/mipmap-*.
# O ícone com o logo do jogo fica só local, em app/src/debug/res (fora do git).
Add-Type -AssemblyName System.Drawing
$res = Join-Path $PSScriptRoot "..\..\app\src\main\res"
$sizes = @{ mdpi = 48; hdpi = 72; xhdpi = 96; xxhdpi = 144; xxxhdpi = 192 }

foreach ($k in $sizes.Keys) {
    $s = $sizes[$k]
    $bmp = New-Object Drawing.Bitmap $s, $s
    $g = [Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = 'AntiAlias'
    $g.Clear([Drawing.Color]::Transparent)

    # Fundo: quadrado arredondado com degradê azul-noite -> violeta.
    $r = [int]($s * 0.18)
    $bg = New-Object Drawing.Drawing2D.GraphicsPath
    $bg.AddArc(0, 0, $r * 2, $r * 2, 180, 90); $bg.AddArc($s - $r * 2 - 1, 0, $r * 2, $r * 2, 270, 90)
    $bg.AddArc($s - $r * 2 - 1, $s - $r * 2 - 1, $r * 2, $r * 2, 0, 90); $bg.AddArc(0, $s - $r * 2 - 1, $r * 2, $r * 2, 90, 90)
    $bg.CloseFigure()
    $grad = New-Object Drawing.Drawing2D.LinearGradientBrush (New-Object Drawing.Point 0, 0), (New-Object Drawing.Point $s, $s),
        ([Drawing.Color]::FromArgb(255, 14, 18, 52)), ([Drawing.Color]::FromArgb(255, 70, 30, 110))
    $g.FillPath($grad, $bg)
    $g.SetClip($bg)

    # Estrelas pequenas de fundo.
    $dot = New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb(170, 255, 255, 255))
    foreach ($pt in @(@(0.18, 0.2), @(0.33, 0.12), @(0.12, 0.45), @(0.85, 0.55), @(0.7, 0.86), @(0.5, 0.3))) {
        $d = [Math]::Max(1, $s * 0.018)
        $g.FillEllipse($dot, [float]($pt[0] * $s), [float]($pt[1] * $s), [float]$d, [float]$d)
    }

    # Planeta com sombra (degradê) e anel inclinado, parte de trás e da frente.
    $cx = $s * 0.46; $cy = $s * 0.58; $pr = $s * 0.26
    $ring = New-Object Drawing.Pen ([Drawing.Color]::FromArgb(230, 255, 196, 92)), ([float]($s * 0.035))
    $state = $g.Save()
    $g.TranslateTransform([float]$cx, [float]$cy); $g.RotateTransform(-20)
    $g.DrawArc($ring, [float](-$pr * 1.7), [float](-$pr * 0.45), [float]($pr * 3.4), [float]($pr * 0.9), 180, 180)
    $g.Restore($state)
    $planet = New-Object Drawing.Drawing2D.GraphicsPath
    $planet.AddEllipse([float]($cx - $pr), [float]($cy - $pr), [float]($pr * 2), [float]($pr * 2))
    $pb = New-Object Drawing.Drawing2D.PathGradientBrush $planet
    $pb.CenterPoint = New-Object Drawing.PointF ([float]($cx - $pr * 0.35)), ([float]($cy - $pr * 0.4))
    $pb.CenterColor = [Drawing.Color]::FromArgb(255, 120, 230, 200)
    $pb.SurroundColors = @([Drawing.Color]::FromArgb(255, 20, 90, 120))
    $g.FillPath($pb, $planet)
    $state = $g.Save()
    $g.TranslateTransform([float]$cx, [float]$cy); $g.RotateTransform(-20)
    $g.DrawArc($ring, [float](-$pr * 1.7), [float](-$pr * 0.45), [float]($pr * 3.4), [float]($pr * 0.9), 0, 180)
    $g.Restore($state)

    # Estrela de quatro pontas no canto superior direito.
    $sx = $s * 0.74; $sy = $s * 0.26; $a = $s * 0.16; $b = $s * 0.035
    $star = New-Object Drawing.Drawing2D.GraphicsPath
    $star.AddPolygon(@(
        (New-Object Drawing.PointF ([float]$sx), ([float]($sy - $a))),
        (New-Object Drawing.PointF ([float]($sx + $b)), ([float]($sy - $b))),
        (New-Object Drawing.PointF ([float]($sx + $a)), ([float]$sy)),
        (New-Object Drawing.PointF ([float]($sx + $b)), ([float]($sy + $b))),
        (New-Object Drawing.PointF ([float]$sx), ([float]($sy + $a))),
        (New-Object Drawing.PointF ([float]($sx - $b)), ([float]($sy + $b))),
        (New-Object Drawing.PointF ([float]($sx - $a)), ([float]$sy)),
        (New-Object Drawing.PointF ([float]($sx - $b)), ([float]($sy - $b)))))
    $g.FillPath((New-Object Drawing.SolidBrush ([Drawing.Color]::FromArgb(255, 255, 240, 200))), $star)

    $g.Dispose()
    $dir = Join-Path $res "mipmap-$k"
    New-Item -ItemType Directory -Force $dir | Out-Null
    $bmp.Save((Join-Path $dir "ic_launcher.png"), [Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
}
