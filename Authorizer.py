import json

def lambda_handler(event, context):
    print(event)
    
    token = event.get('authorizationToken', '')
    
    # Formato esperado para pruebas simples: "Bearer tenant_id:usuario_id:rol"
    try:
        if token.startswith("Bearer "):
            token_data = token.replace("Bearer ", "")
            parts = token_data.split(":")
            
            tenant_id = parts[0]
            usuario_id = parts[1]
            rol = parts[2]
            
            return {
                "principalId": usuario_id,
                "policyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": "execute-api:Invoke",
                            "Effect": "Allow",
                            "Resource": "*"
                        }
                    ]
                },
                "context": {
                    "tenant_id": tenant_id,
                    "usuario_id": usuario_id,
                    "rol": rol
                }
            }
    except Exception as e:
        print(f"Error procesando token: {e}")
        
    raise Exception("Unauthorized")