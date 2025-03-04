from django.urls import get_resolver
import json
from datetime import datetime

def generate_api_documentation():
    """
    Generate API documentation by inspecting URL patterns
    Returns a dictionary containing API endpoint information
    """
    resolver = get_resolver()
    api_docs = {
        "info": {
            "title": "API Documentation",
            "version": "1.0.0",
            "generated_at": datetime.now().isoformat(),
        },
        "endpoints": []
    }
    
    def process_pattern(pattern, prefix=""):
        if hasattr(pattern, "url_patterns"):
            # This is a URLResolver (includes are handled here)
            for p in pattern.url_patterns:
                process_pattern(p, prefix + str(pattern.pattern))
        else:
            # This is a URLPattern
            endpoint = {
                "path": prefix + str(pattern.pattern),
                "name": pattern.name or "",
                "method": "GET",  # Default method, you might want to inspect view for actual methods
            }
            
            # Try to get view documentation
            if hasattr(pattern.callback, "__doc__") and pattern.callback.__doc__:
                endpoint["description"] = pattern.callback.__doc__.strip()
            else:
                endpoint["description"] = "No description available"
                
            api_docs["endpoints"].append(endpoint)

    # Process all URL patterns
    for pattern in resolver.url_patterns:
        process_pattern(pattern)
    
    return api_docs

# Usage example
if __name__ == "__main__":
    docs = generate_api_documentation()
    
    # Save to JSON file
    with open("api_documentation.json", "w") as f:
        json.dump(docs, f, indent=2)
        
        