import boto3
import uuid
import os
import json
import hashlib
from datetime import datetime

def lambda_handler(event, context):
    print(event)
    
    # Manejar body como string o dict
    body = json.loads(event['body']) if isinstance(event.get('body'), str) else event.get('body', {})
    
    nombre_empresa = body.get('nombre_empresa')
    rubro = body.get('rubro', 'No especificado')
    nombre_admin = body.get('nombre_admin')
    correo = body.get('correo')
    contrasena = body.get('contrasena')
    
    if not nombre_empresa or not correo or not contrasena:
        return {
            'statusCode': 400,
            'body': json.dumps({'codigo': 'datos_incompletos', 'mensaje': 'Faltan campos obligatorios'})
        }
    
    tabla_tenants = os.environ.get("TABLE_TENANTS", "t_tenants")
    tabla_usuarios = os.environ.get("TABLE_USUARIOS", "t_usuarios")
    sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
    
    # Generar identificadores y hash de contraseña
    uuid_raw = str(uuid.uuid4()).replace('-', '')[:8]
    tenant_id = f"ten_{uuid_raw}"
    usuario_id = f"usr_{uuid_raw}"
    fecha_creacion = datetime.utcnow().isoformat() + "Z"
    
    contrasena_hash = hashlib.sha256(contrasena.encode('utf-8')).hexdigest()
    
    # 1. Guardar Tenant en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table_tenants = dynamodb.Table(tabla_tenants)
    
    # Verificar que la empresa no esté registrada (ignora mayúsculas y espacios extra)
    nombre_normalizado = ' '.join(nombre_empresa.strip().lower().split())
    scan_kwargs = {'ProjectionExpression': '#n', 'ExpressionAttributeNames': {'#n': 'nombre'}}
    while True:
        response_scan = table_tenants.scan(**scan_kwargs)
        for item in response_scan.get('Items', []):
            if ' '.join(item.get('nombre', '').strip().lower().split()) == nombre_normalizado:
                return {
                    'statusCode': 409,
                    'body': json.dumps({'codigo': 'empresa_existente', 'mensaje': 'La empresa ya se encuentra registrada'})
                }
        if 'LastEvaluatedKey' not in response_scan:
            break
        scan_kwargs['ExclusiveStartKey'] = response_scan['LastEvaluatedKey']
    
    item_tenant = {
        'tenant_id': tenant_id,
        'nombre': nombre_empresa,
        'rubro': rubro,
        'estado': 'activo',
        'fecha_creacion': fecha_creacion
    }
    response_tenant = table_tenants.put_item(Item=item_tenant)
    
    # 2. Guardar Usuario Admin en DynamoDB
    table_usuarios = dynamodb.Table(tabla_usuarios)
    
    item_usuario = {
        'tenant_id': tenant_id,
        'usuario_id': usuario_id,
        'nombre': nombre_admin,
        'correo': correo,
        'contrasena_hash': contrasena_hash,
        'rol': 'admin',
        'estado': 'activo',
        'fecha_creacion': fecha_creacion
    }
    response_usuario = table_usuarios.put_item(Item=item_usuario)
    
    # 3. Publicar evento en SNS
    if sns_topic_arn:
        try:
            sns = boto3.client('sns')
            evento = {
                'evento_id': f"evt_{str(uuid.uuid4())[:8]}",
                'tipo': 'usuario.creado',
                'tenant_id': tenant_id,
                'fecha': fecha_creacion,
                'datos': {
                    'usuario_id': usuario_id,
                    'nombre': nombre_admin,
                    'rol': 'admin'
                }
            }
            sns.publish(
                TopicArn=sns_topic_arn,
                Message=json.dumps(evento)
            )
        except Exception as e_sns:
            print(f"Advertencia: No se pudo publicar en SNS (Topico no encontrado):         ")
        
    return {
        'statusCode': 201,
        'body': json.dumps({
            'mensaje': 'Tenant y usuario admin creados exitosamente',
            'tenant_id': tenant_id,
            'usuario_id': usuario_id
        })
    }