from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import json

with open("graph.json") as f:
    GRAPH = json.load(f)
    
def find_all_target_nodes(node_id):
    target_nodes = []
    for link in GRAPH["links"]:
        if link["source"] == node_id:
            target_nodes.append(link["target"])
    return target_nodes

class GraphServer(BaseHTTPRequestHandler):
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/":
            source = 0
            target_nodes = find_all_target_nodes(source)
        elif path.startswith("/node/"):
            source = int(path.split("/")[-1])
            target_nodes = find_all_target_nodes(source)
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return

        if target_nodes:
            html_links = "<ul>\n"
            for target in target_nodes:
                html_links += f'<li><a href="/node/{target}">{target}</a></li>\n'
            html_links += "</ul>\n"
        else:
            html_links = "<p>Stąd nie wychodzą żadne odnośniki.</p>\n"
            
        with open("page_template.html", "rt", encoding="utf8") as f:
            html_content = f.read()
            html_content = html_content.replace("{{ source }}", str(source))
            html_content = html_content.replace("{{ html_links }}", html_links)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))

httpd = HTTPServer(("localhost", 21000), GraphServer)
print("Starting server on port 21000...")
httpd.serve_forever()
            
            
            
                
            
            