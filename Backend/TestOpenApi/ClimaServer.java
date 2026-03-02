import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.util.stream.Collectors;

public class ClimaServer {

    public static void main(String[] args) throws Exception {

        HttpServer server = HttpServer.create(new InetSocketAddress(8080), 0);
        server.createContext("/clima", new ClimaHandler());
        server.setExecutor(null);

        System.out.println("Servidor iniciado en http://localhost:8080");
        server.start();
    }

    static class ClimaHandler implements HttpHandler {

        @Override
        public void handle(HttpExchange exchange) throws IOException {

            // Permitir CORS
            exchange.getResponseHeaders().add("Access-Control-Allow-Origin", "*");

            if ("POST".equals(exchange.getRequestMethod())) {

                String body = new BufferedReader(
                        new InputStreamReader(exchange.getRequestBody(), StandardCharsets.UTF_8))
                        .lines()
                        .collect(Collectors.joining("\n"));

                String[] coords = body.split(",");
                String latitude = coords[0];
                String longitude = coords[1];

                String url = "https://api.open-meteo.com/v1/forecast?latitude="
                        + latitude
                        + "&longitude="
                        + longitude
                        + "&current_weather=true"
                        + "&hourly=precipitation,precipitation_probability"
                        + "&timezone=America/Bogota";

                try {
                    HttpClient client = HttpClient.newHttpClient();
                    HttpRequest request = HttpRequest.newBuilder()
                            .uri(URI.create(url))
                            .GET()
                            .build();

                    HttpResponse<String> response =
                            client.send(request, HttpResponse.BodyHandlers.ofString());

                    String jsonResponse = response.body();

                    byte[] responseBytes = jsonResponse.getBytes(StandardCharsets.UTF_8);

                    exchange.sendResponseHeaders(200, 0); // 0 = chunked encoding automático

                    OutputStream os = exchange.getResponseBody();
                    os.write(responseBytes);
                    os.close();

                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }
    }
}