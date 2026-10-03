from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from database import engine, Base
from config import settings
from api.endpoints import sops, ai, checklists

Base.metadata.create_all(bind=engine)

app = FastAPI(title='Dental AI Platform', version='1.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
    allow_headers=['Content-Type', 'Authorization'],
)

app.include_router(sops.router, prefix='/api/sops', tags=['sops'])
app.include_router(ai.router, prefix='/api/ai', tags=['ai'])
app.include_router(checklists.router, prefix='/api/checklists', tags=['checklists'])

@app.get('/health')
def health_check():
    return {'status': 'ok'}

@app.api_route('/api/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'], include_in_schema=False)
def unknown_api(path: str):
    raise HTTPException(status_code=404, detail='Not Found')

# Mount last so API, health and documentation routes take precedence.
app.mount('/', StaticFiles(directory=Path(__file__).resolve().parent.parent / 'frontend', html=True), name='frontend')

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=9090)
