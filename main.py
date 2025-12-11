# grid_alpha_calibrated
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from agents import LibrarianAgent, InterfaceEngineerAgent, SecurityAuditorAgent

app = FastAPI()

class QueryRequest(BaseModel):
    query: str


librarian = LibrarianAgent()
engineer = InterfaceEngineerAgent()
auditor = SecurityAuditorAgent()

@app.post("/query")
async def query_eip(request: QueryRequest):
    try:
        # retrieve
        retrieval_docs = librarian.retrieve(request.query)
        
        # generate
        current_code = engineer.generate(request.query, retrieval_docs)

        # eval
        metrics = engineer.evaluate_precision(request.query, retrieval_docs)
        
        # audit loop
        audit_log = []
        max_retries = 2
        
        for i in range(max_retries):
            audit_result = auditor.audit(current_code)
            audit_log.append({"attempt": i+1, "status": audit_result['status'], "feedback": audit_result['feedback']})
            
            if audit_result['status'] == "PASS":
                break
            else:
                current_code = engineer.refine(current_code, audit_result['feedback'])
        

        
        return {
            "query": request.query,
            "final_response": current_code,
            "audit_trail": audit_log,
            "retrieval_count": len(retrieval_docs),
            "retrieved_documents": [doc['metadata'] for doc in retrieval_docs],
            "quality_metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8123)
