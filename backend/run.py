import uvicorn
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if __name__ == '__main__':
    print('Dental AI Platform, port 9090')
    print('Swagger: http://localhost:9090/docs')
    uvicorn.run('main:app', host='127.0.0.1', port=9090, reload=True)
