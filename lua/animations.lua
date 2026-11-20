-- =====================================================
-- Arch Linux Hyprland Rice — Animations Configuration
-- Engine: Hyprland Lua Configuration (v0.57.2+)
-- macOS-inspired fluid motion system
-- =====================================================

-- ── Bezier Curve Library ───────────────────────────────────────────────────
-- macOS spring: fast deceleration, overshoots just barely, settles cleanly
hl.curve("macosSpring",     { type = "bezier", points = { {0.25, 1.0},  {0.5, 1.0}  } })
-- macOS ease-out: sharp start, long gentle tail (windows opening)
hl.curve("macosOut",        { type = "bezier", points = { {0.16, 1.0},  {0.3, 1.0}  } })
-- macOS ease-in-out: symmetric flow (workspace transitions)
hl.curve("macosInOut",      { type = "bezier", points = { {0.45, 0.0},  {0.55, 1.0} } })
-- macOS closing: quick confident exit, no linger
hl.curve("macosClose",      { type = "bezier", points = { {0.55, 0.0},  {1.0, 0.85} } })
-- Gentle fade: soft and silky (opacity transitions)
hl.curve("macosFade",       { type = "bezier", points = { {0.4,  0.0},  {0.6, 1.0}  } })
-- Border highlight: snappy micro-transition
hl.curve("macosSnap",       { type = "bezier", points = { {0.0,  0.9},  {0.1, 1.0}  } })
-- Workspace slide: momentum with clean stop
hl.curve("macosSlide",      { type = "bezier", points = { {0.25, 0.46}, {0.45, 0.94} } })

-- ── Window Animations ─────────────────────────────────────────────────────
-- windows: base fallback for any unspecified child
hl.animation({ leaf = "windows",          enabled = true, speed = 3.0,  bezier = "macosOut"    })

-- windowsIn: opening — gentle scale-up with fade, feels like macOS app launch
hl.animation({ leaf = "windowsIn",        enabled = true, speed = 2.8,  bezier = "macosSpring" })

-- windowsOut: closing — quick confident shrink, no sluggish hang
hl.animation({ leaf = "windowsOut",       enabled = true, speed = 2.5,  bezier = "macosClose"  })

-- windowsMove: dragging / tiling repositions — spring snaps to target
hl.animation({ leaf = "windowsMove",      enabled = true, speed = 3.5,  bezier = "macosSpring" })

-- ── Fade / Opacity Transitions ────────────────────────────────────────────
-- fadeIn: layers, popups, notifications appearing — silky onset
hl.animation({ leaf = "fadeIn",           enabled = true, speed = 3.0,  bezier = "macosFade"   })

-- fadeOut: layers disappearing — slightly faster so it feels decisive
hl.animation({ leaf = "fadeOut",          enabled = true, speed = 2.5,  bezier = "macosFade"   })

-- fadeLayers: Waybar / Rofi / Quick-Settings layer surface fades
hl.animation({ leaf = "fadeLayers",       enabled = true, speed = 3.0,  bezier = "macosFade"   })

-- fadeShadow: shadow follows window opacity cleanly
hl.animation({ leaf = "fadeShadow",       enabled = true, speed = 3.0,  bezier = "macosFade"   })

-- fadeDim: inactive-window dimming on focus change
hl.animation({ leaf = "fadeDim",          enabled = true, speed = 2.5,  bezier = "macosFade"   })

-- fadeSwitch: fade when switching workspaces (cross-fade feel)
hl.animation({ leaf = "fadeSwitch",       enabled = true, speed = 2.8,  bezier = "macosFade"   })

-- ── Border ────────────────────────────────────────────────────────────────
-- border: active/inactive border color crossfade — snappy micro-beat
hl.animation({ leaf = "border",           enabled = true, speed = 4.0,  bezier = "macosSnap"   })
hl.animation({ leaf = "borderangle",      enabled = true, speed = 4.0,  bezier = "macosSnap"   })

-- ── Workspace Transitions ─────────────────────────────────────────────────
-- workspaces: lateral slide — fluid momentum, no rubber-band
hl.animation({ leaf = "workspaces",       enabled = true, speed = 3.8,  bezier = "macosSlide"  })

-- specialWorkspace: scratchpad / special WS — gentle pop from bottom
hl.animation({ leaf = "specialWorkspace", enabled = true, speed = 3.5,  bezier = "macosSpring" })
