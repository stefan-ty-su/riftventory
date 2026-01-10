"""
Card OCR Backend Service using EasyOCR
"""
import base64
import io
import re
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import easyocr
import numpy as np
from PIL import Image

app = FastAPI(title="Card OCR Service", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize EasyOCR reader (lazy load on first request)
reader: Optional[easyocr.Reader] = None

# Store scanned cards
scanned_cards: list[str] = []


def get_reader() -> easyocr.Reader:
    """Lazy initialize EasyOCR reader."""
    global reader
    if reader is None:
        print("Initializing EasyOCR reader...")
        reader = easyocr.Reader(['en'], gpu=False)
        print("EasyOCR reader ready.")
    return reader


# Request/Response models
class OCRRequest(BaseModel):
    image: str  # Base64 encoded image
    mode: str = "full"  # "full", "tcg", "traditional"


class RegionResult(BaseModel):
    text: str
    confidence: float
    label: str


class OCRResponse(BaseModel):
    success: bool
    raw_text: str
    confidence: float
    regions: Optional[dict] = None
    card_type: Optional[str] = None
    detected_rank: Optional[str] = None
    detected_suit: Optional[str] = None
    bounding_boxes: Optional[list] = None


class StreamScanResponse(BaseModel):
    success: bool
    card_detected: bool
    card_id: Optional[str] = None
    already_scanned: bool = False


class ScannedCardsResponse(BaseModel):
    cards: list[str]
    count: int


# Card ID pattern: 2-4 uppercase letters, any spaces, 2-4 digit number, optional /total
CARD_ID_PATTERN = re.compile(r'([A-Z]{2,4})\s+(\d{3})(?:/(\d{3}))?')

def decode_image(base64_string: str) -> Image.Image:
    """Decode base64 image string to PIL Image."""
    # Remove data URL prefix if present
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    
    image_data = base64.b64decode(base64_string)
    image = Image.open(io.BytesIO(image_data))
    
    # Convert to RGB if necessary
    if image.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    return image


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "card-ocr"}


def extract_card_id(img_array: np.ndarray, ocr: easyocr.Reader) -> Optional[str]:
    """Extract card ID from image array."""
    results = ocr.readtext(img_array)
    texts = [text for _, text, _ in results]
    full_text = " ".join(texts)

    for match in CARD_ID_PATTERN.finditer(full_text):
        set_code = match.group(1)
        card_num = match.group(2)
        total_cards = match.group(3)
        if total_cards:
            return f"{set_code} {card_num.zfill(3)}/{total_cards}"
        else:
            return f"{set_code} {card_num.zfill(3)}"
    return None


@app.post("/scan-stream", response_model=StreamScanResponse)
async def scan_stream_frame(request: OCRRequest):
    """
    Scan a video frame for cards and add to scanned list.
    Returns whether a new card was detected.
    """
    try:
        ocr = get_reader()
        image = decode_image(request.image)
        img_array = np.array(image)

        card_id = extract_card_id(img_array, ocr)

        if card_id:
            already_scanned = card_id in scanned_cards
            if not already_scanned:
                scanned_cards.append(card_id)

            return StreamScanResponse(
                success=True,
                card_detected=True,
                card_id=card_id,
                already_scanned=already_scanned
            )

        return StreamScanResponse(
            success=True,
            card_detected=False
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scanned-cards", response_model=ScannedCardsResponse)
async def get_scanned_cards():
    """Get list of all scanned cards."""
    return ScannedCardsResponse(
        cards=scanned_cards,
        count=len(scanned_cards)
    )


@app.delete("/scanned-cards")
async def clear_scanned_cards():
    """Clear the list of scanned cards."""
    scanned_cards.clear()
    return {"success": True, "message": "Scanned cards cleared"}


@app.post("/ocr", response_model=OCRResponse)
async def perform_ocr(request: OCRRequest):
    """
    Perform OCR on a card image.

    Modes:
    - full: Full image OCR
    - tcg: Region-based OCR for trading cards
    - traditional: Optimized for playing cards (rank/suit detection)
    """
    try:
        ocr = get_reader()
        image = decode_image(request.image)
        img_array = np.array(image)

        if request.mode == "tcg":
            # Full image OCR with regex matching for card IDs
            results = ocr.readtext(img_array)

            texts = []
            confidences = []

            for _, text, conf in results:
                texts.append(text)
                confidences.append(conf)

            full_text = " ".join(texts)
            avg_confidence = (sum(confidences) / len(confidences) * 100) if confidences else 0
            print(full_text)
            # Find card IDs using regex
            card_ids = []
            for match in CARD_ID_PATTERN.finditer(full_text):
                set_code = match.group(1)
                card_num = match.group(2)
                total_cards = match.group(3)
                if total_cards:
                    formatted_id = f"{set_code} {card_num.zfill(3)}/{total_cards}"
                else:
                    formatted_id = f"{set_code} {card_num.zfill(3)}"
                card_ids.append(formatted_id)

            regions_result = {
                "card_id": {
                    "text": ", ".join(card_ids) if card_ids else "",
                    "confidence": round(avg_confidence, 1),
                    "label": "Card ID"
                }
            }

            return OCRResponse(
                success=True,
                raw_text=full_text,
                confidence=round(avg_confidence, 1),
                regions=regions_result,
                card_type="Trading Card (TCG)"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
