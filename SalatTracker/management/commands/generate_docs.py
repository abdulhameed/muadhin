from django.core.management.base import BaseCommand
from django.urls import get_resolver
import json
from datetime import datetime

class Command(BaseCommand):
    help = 'Generate API documentation in JSON format'

    def handle(self, *args, **options):
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
                for p in pattern.url_patterns:
                    process_pattern(p, prefix + str(pattern.pattern))
            else:
                endpoint = {
                    "path": prefix + str(pattern.pattern),
                    "name": pattern.name or "",
                    "method": "GET",
                }
                
                if hasattr(pattern.callback, "__doc__") and pattern.callback.__doc__:
                    endpoint["description"] = pattern.callback.__doc__.strip()
                else:
                    endpoint["description"] = "No description available"
                    
                api_docs["endpoints"].append(endpoint)

        for pattern in resolver.url_patterns:
            process_pattern(pattern)
        
        with open("api_documentation.json", "w") as f:
            json.dump(api_docs, f, indent=2)
            
        self.stdout.write(self.style.SUCCESS('Successfully generated API documentation'))
