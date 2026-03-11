from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Character Counter API")


class TextInput(BaseModel):
    text: str


class PredictionResult(BaseModel):
    text: str
    character_count: int
    word_count: int
    whitespace_count: int
    non_whitespace_count: int


@app.post("/predict", response_model=PredictionResult)
def predict(payload: TextInput):
    text = payload.text
    return PredictionResult(
        text=text,
        character_count=len(text),
        word_count=len(text.split()) if text.strip() else 0,
        whitespace_count=sum(1 for c in text if c.isspace()),
        non_whitespace_count=sum(1 for c in text if not c.isspace()),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)