from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse


class ProstaObslugaZapytan(BaseHTTPRequestHandler):
    def do_GET(self):
        """Obsługa żądań GET"""
        # Parsowanie ścieżki URL i parametrów zapytania
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        # Różne odpowiedzi w zależności od ścieżki
        if path == "/":
            # Strona główna
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()

            content = """
            <html>
                <head><title>Prosty Serwer HTTP</title></head>
                <body>
                    <h1>Witaj na prostym serwerze HTTP!</h1>
                    <p>Dostępne endpointy:</p>
                    <ul>
                        <li>/hello - podstawowe powitanie</li>
                        <li>/echo?message=tekst - zwraca przekazany tekst</li>
                        <li>/json - przykładowa odpowiedź JSON</li>
                    </ul>
                </body>
            </html>
            """
            self.wfile.write(content.encode("utf-8"))

        elif path == "/hello":
            # Prosty endpoint tekstowy
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("Cześć! To jest prosty serwer HTTP.".encode("utf-8"))

        elif path == "/echo":
            # Echo parametru z zapytania
            message = query_params.get("message", [""])[0]
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"Otrzymana wiadomość: {message}".encode("utf-8"))

        elif path == "/json":
            # Przykład odpowiedzi JSON
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            data = {"message": "To jest odpowiedź JSON", "status": "ok", "code": 200}
            self.wfile.write(json.dumps(data).encode("utf-8"))

        else:
            # Obsługa nieznalezionej ścieżki
            self.send_response(404)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("404 - Nie znaleziono strony".encode("utf-8"))

    def do_POST(self):
        """Obsługa żądań POST"""
        if self.path == "/submit":
            # Odczytanie długości danych
            content_length = int(self.headers["Content-Length"])
            # Odczytanie danych z żądania
            post_data = self.rfile.read(content_length)

            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"Otrzymane dane POST: {post_data.decode('utf-8')}".encode("utf-8")
            )
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("404 - Endpoint nie istnieje".encode("utf-8"))


def uruchom_serwer(port=8000):
    """Uruchamia serwer HTTP na określonym porcie"""
    server_address = ("", port)
    httpd = HTTPServer(server_address, ProstaObslugaZapytan)
    print(f"Uruchamiam serwer na porcie {port}...")
    httpd.serve_forever()


if __name__ == "__main__":
    uruchom_serwer()
