from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

@app.get('/')
def root():
    return {'message': 'Dental AI Platform API', 'version': '1.0.0', 'port': 9090}

@app.get('/health')
def health_check():
    return {'status': 'ok'}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=9090)
