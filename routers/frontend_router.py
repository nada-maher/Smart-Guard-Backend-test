from fastapi import APIRouter

frontend_router = APIRouter()

@frontend_router.get("/")
def root():
    return {"message": "Frontend router placeholder"}
