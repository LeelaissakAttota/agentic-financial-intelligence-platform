# GitHub Social Preview Design Specification

## Image Specifications
- **Dimensions:** 1280 x 640 pixels (2:1 aspect ratio)
- **Format:** PNG (preferred) or JPEG
- **Color Space:** sRGB
- **File Size:** < 1MB for optimal loading

## Design Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                        FINANCIAL RESEARCH AGENT                         │  │
│  │                                                                          │  │
│  │    An autonomous AI financial research assistant using LLM agents,     │  │
│  │    RAG pipelines, document intelligence, and multi-agent workflows     │  │
│  │    to generate investment research reports.                            │  │
│  │                                                                          │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │   PLANNER    │ │   DATA       │ │   WEB        │ │   DOCUMENT   │       │
│  │   AGENT      │ │   AGENT      │ │   AGENT      │ │   AGENT      │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │  ANALYSIS    │ │   RAG        │ │   REPORT     │ │   MEMORY     │       │
│  │   AGENT      │ │   AGENT      │ │   AGENT      │ │   AGENT      │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  🤖  Powered by LangGraph  •  🧠  Claude 3.5 Sonnet  •  🔍  RAG      │  │
│  │  📊  ChromaDB  •  🐘  PostgreSQL+pgvector  •  ⚡  Async Parallel      │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Color Palette

| Element | Hex | RGB | Usage |
|---------|-----|-----|-------|
| Primary Dark | `#0D1B2A` | (13, 27, 42) | Background, headers |
| Primary Blue | `#1B4F72` | (27, 79, 114) | Agent cards, borders |
| Accent Blue | `#3A86C8` | (58, 134, 200) | Highlights, links |
| Accent Gold | `#E6A53C` | (230, 165, 60) | Key metrics, badges |
| White | `#FFFFFF` | (255, 255, 255) | Text on dark |
| Light Gray | `#E0E0E0` | (224, 224, 224) | Secondary text |
| Success Green | `#2E7D32` | (46, 125, 50) | Status indicators |
| Error Red | `#C62828` | (198, 40, 40) | Error states |

## Typography

| Element | Font | Size | Weight | Color |
|---------|------|------|--------|-------|
| Main Title | Inter / Roboto | 48px | Bold (700) | White |
| Subtitle | Inter / Roboto | 24px | Regular (400) | Light Gray |
| Agent Labels | Inter / Roboto | 16px | Medium (500) | White |
| Tech Stack Labels | Inter / Roboto | 14px | Regular (400) | Light Gray |
| Footer Tech | Inter / Roboto | 12px | Regular (400) | Accent Gold |

## Visual Elements

### Agent Cards (8 total, 2 rows of 4)
- **Dimensions:** 280 x 120px each
- **Spacing:** 20px gap
- **Border Radius:** 12px
- **Background:** Linear gradient `#0D1B2A` → `#1B4F72`
- **Border:** 2px solid `#3A86C8`
- **Icon:** 32px financial-themed icons (📊, 🌐, 📄, 🧠, 📈, 🔍, 📝, 🧠)

### Tech Stack Footer
- **Background:** Semi-transparent `#0D1B2A` at 90% opacity
- **Icons:** Small tech logos (LangGraph, Claude, ChromaDB, PostgreSQL, FastAPI, Streamlit)

## Alternative Compact Version (for smaller previews)

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│   FINANCIAL RESEARCH AGENT                               │
│   Autonomous AI Financial Research Assistant            │
│                                                          │
│   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │
│   │ PLANNER│ │  DATA  │ │  WEB   │ │  DOC   │           │
│   └────────┘ └────────┘ └────────┘ └────────┘           │
│   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │
│   │ANALYSIS│ │  RAG   │ │ REPORT │ │ MEMORY │           │
│   └────────┘ └────────┘ └────────┘ └────────┘           │
│                                                          │
│   LangGraph • Claude 3.5 • RAG • ChromaDB • PostgreSQL  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

## Implementation Notes

### For Designers (Figma/Sketch/Adobe)
1. Create 1280x640 artboard
2. Use Inter font family (Google Fonts - free)
2. Apply dark theme with blue accent
3. Use consistent 8px grid system
4. Export as PNG @ 2x for retina

### For Developers (Programmatic Generation)
```python
# Can be generated with Pillow or similar
from PIL import Image, ImageDraw, ImageFont

def generate_social_preview():
    img = Image.new('RGB', (1280, 640), '#0D1B2A')
    draw = ImageDraw.Draw(img)
    # ... rendering logic
    img.save('social_preview.png')
```

### GitHub Settings
1. Go to Settings → General → Social Preview
2. Upload generated `social_preview.png`
3. Verify at: `https://github.com/username/financial-research-agent`

## Brand Assets Location
```
docs/
├── images/
│   ├── social_preview.png          # 1280x640 main preview
│   ├── social_preview@2x.png       # 2560x1280 retina
│   ├── og_image.png                # Open Graph (same as social)
│   ├── twitter_card.png            # Twitter Card (1200x628)
│   ├── favicon.ico                 # 32x32
│   ├── logo.svg                    # Vector logo
│   └── logo_with_text.svg          # Logo with project name
└── brand/
    ├── color_palette.json          # For developers
    └── typography.json             # Font specs
```