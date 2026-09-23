from fastapi import Request

def get_client_ip(request: Request) -> str:
    """
    Extract the real client IP address, safely handling X-Forwarded-For 
    if the application is running behind a trusted proxy.
    """
    # If there is an X-Forwarded-For header, it typically contains a comma-separated
    # list of IPs: "client, proxy1, proxy2". The first element is the original client.
    # Warning: Without a trusted proxy correctly configuring this header, it is spoofable.
    # In a real production deployment, this should only be trusted if we know we are 
    # behind our own reverse proxy that strips spoofed headers from the outside.
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    # Fallback to the direct TCP connection peer
    if request.client and request.client.host:
        return request.client.host
    
    return "unknown"
