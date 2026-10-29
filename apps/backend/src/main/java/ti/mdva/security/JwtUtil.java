package ti.mdva.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class JwtUtil {

    /**
     * Default secret declarado en application.yml. En perfil 'prod' este valor
     * está prohibido — debe sobreescribirse vía variable de entorno JWT_SECRET.
     * Mantener sincronizado con application.yml.
     */
    public static final String DEFAULT_DEV_SECRET =
            "cambiame-dev-jwt-secret-de-al-menos-256-bits-para-hs256-signing";

    private final SecretKey key;
    private final long expirationMs;

    public JwtUtil(@Value("${mdva.jwt.secret}") String secret,
                   @Value("${mdva.jwt.expiration-ms}") long expirationMs,
                   @Value("${spring.profiles.active:}") String activeProfile) {

        if (isProdProfile(activeProfile) && isInsecureSecret(secret)) {
            throw new IllegalStateException(
                "JWT secret no puede ser el default ni estar vacío en perfil 'prod'. " +
                "Configura la variable de entorno JWT_SECRET con un secret de al menos 256 bits."
            );
        }

        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.expirationMs = expirationMs;
    }

    private static boolean isProdProfile(String activeProfile) {
        if (activeProfile == null || activeProfile.isBlank()) return false;
        for (String p : activeProfile.split(",")) {
            if ("prod".equalsIgnoreCase(p.trim())) return true;
        }
        return false;
    }

    private static boolean isInsecureSecret(String secret) {
        return secret == null || secret.isBlank() || DEFAULT_DEV_SECRET.equals(secret);
    }

    public long getExpirationMs() {
        return expirationMs;
    }

    public String generateToken(String username, Long userId) {
        Date now = new Date();
        Date expiry = new Date(now.getTime() + expirationMs);

        return Jwts.builder()
                .subject(username)
                .claim("userId", userId)
                .issuedAt(now)
                .expiration(expiry)
                .signWith(key)
                .compact();
    }

    public String extractUsername(String token) {
        return extractClaims(token).getSubject();
    }

    public boolean validateToken(String token) {
        try {
            extractClaims(token);
            return true;
        } catch (JwtException | IllegalArgumentException e) {
            return false;
        }
    }

    private Claims extractClaims(String token) {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}
