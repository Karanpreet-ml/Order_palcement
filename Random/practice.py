import os

class RiskDemo:
    def __init__(self):
        self.secret_key = os.getenv("SECRET_KEY")
    
    def _calculate_secure_hash(self, payload):
        """
        DEAD ABSTRACTION: This complex logic is defined but 
        never called within this module or exported.
        """
        import hashlib
        return hashlib.sha256(payload.encode()).hexdigest()

    def process_request(self, request_data):
        # DEFENSIVE MISMATCH: Redundant/Confusing null check 
        # that doesn't protect the actual usage below.
        if request_data is None:
            print("Warning: Data is missing")
        
        # This will crash if request_data is None, but the AI 
        # flag logic sees the mismatch in defensive intent.
        user_id = request_data["user_id"]
        
        # HALLUCINATED CALL: Calling a method that doesn't 
        # exist in the standard or internal auth libraries.
        from backend.services.auth import auth_service
        is_valid = auth_service.validate_v3_token_strict(user_id)
        
        return is_valid
