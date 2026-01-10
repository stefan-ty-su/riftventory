EasyOCR feasiblity test. (Changed to tesseract, would probably use different implementation when using React/Expo)
Web-based OCR application for detecting text on trading cards and traditional playing cards, powered by EasyOCR.

## Features

- **Full Scan Mode**: OCR the entire card image
- **TCG Mode**: Region-based scanning for trading cards (name, type, text, stats)
- **Playing Cards Mode**: Detects rank and suit from traditional cards
- **Camera Support**: Use device camera for live scanning
- **Drag & Drop / Paste**: Easy image input
- **Bounding Box Visualization**: See detected text regions overlaid on the image

## Architecture

```
┌─────────────────┐     HTTP/JSON      ┌─────────────────┐
│   Frontend      │ ◄─────────────────► │   Backend       │
│   (HTML/JS)     │   POST /ocr        │   (FastAPI)     │
│   Port 3000     │                    │   Port 8001     │
└─────────────────┘                    └─────────────────┘
                                              │
                                              ▼
                                       ┌─────────────────┐
                                       │   EasyOCR       │
                                       │   (Python)      │
                                       └─────────────────┘
```

## Quick Start

### Option 1: Docker Compose (Recommended)

```bash
cd card-ocr
docker-compose up --build
```

Then open http://localhost:3000

### Option 2: Manual Setup

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python main.py
```

**Frontend:**
Just open `index.html` in a browser, or serve it:
```bash
python -m http.server 3000
```

## API Endpoints

### Health Check
```
GET /health
```

### OCR
```
POST /ocr
Content-Type: application/json

{
  "image": "data:image/png;base64,...",
  "mode": "full" | "tcg" | "traditional"
}
```

**Response:**
```json
{
  "success": true,
  "raw_text": "Detected text...",
  "confidence": 85.5,
  "regions": { ... },          // TCG mode only
  "card_type": "Trading Card", // When detected
  "detected_rank": "K",        // Traditional mode
  "detected_suit": "♠ Spades", // Traditional mode
  "bounding_boxes": [ ... ]    // Text region coordinates
}
```

## TCG Region Configuration

The default regions are optimized for standard TCG layouts. Adjust in `backend/main.py`:

```python
TCG_REGIONS = {
    "name": {"x": 0.08, "y": 0.03, "w": 0.84, "h": 0.08, "label": "Card Name"},
    "type": {"x": 0.08, "y": 0.55, "w": 0.50, "h": 0.05, "label": "Card Type"},
    "text": {"x": 0.08, "y": 0.60, "w": 0.84, "h": 0.25, "label": "Card Text"},
    "stats": {"x": 0.70, "y": 0.88, "w": 0.25, "h": 0.08, "label": "Stats"},
}
```

Values are percentages (0-1) of card dimensions: `x`, `y` = top-left position; `w`, `h` = width/height.

## Integrating with Riftventory

To add this as an OCR endpoint in your existing FastAPI backend:

1. Copy the EasyOCR functions from `backend/main.py`
2. Add to your `backend/main.py`:

```python
# In requirements.txt, add:
# easyocr
# pillow

# In main.py:
from card_ocr import perform_ocr  # Extract to separate module

@app.post("/cards/ocr")
async def ocr_card(request: OCRRequest):
    return await perform_ocr(request)
```

## Notes

- First request may be slow while EasyOCR downloads models (~100MB)
- GPU support: Change `gpu=False` to `gpu=True` in `get_reader()` if CUDA available
- Traditional card detection works best with clear, well-lit photos showing rank/suit corners
