import warnings

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.compare import router as compare_router

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style, apply openpyxl's default",
    category=UserWarning,
)

app = FastAPI(title="工厂订单数据核对API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(compare_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "工厂订单数据核对API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
