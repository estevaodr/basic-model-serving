from fastapi import HTTPException, Request


def get_classifier(request: Request):
    if not getattr(request.app.state, "ready", False):
        raise HTTPException(status_code=503, detail={"status": "not_ready"})
    return request.app.state.classifier
