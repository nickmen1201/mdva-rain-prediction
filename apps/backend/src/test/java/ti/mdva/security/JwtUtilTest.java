package ti.mdva.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;

import static org.assertj.core.api.Assertions.assertThat;

class JwtUtilTest {

    private static final String SECRET = "test-secret-for-mdva-jwt-signing-needs-256-bits-min";
    private static final long ONE_DAY_MS = 86_400_000L;

    private final JwtUtil jwtUtil = new JwtUtil(SECRET, ONE_DAY_MS, "");

    @Nested
    @DisplayName("generateToken")
    class Generate {

        @Test
        void produceTokenJwtConTresSegmentos() {
            String token = jwtUtil.generateToken("juan01", 42L);
            assertThat(token).isNotBlank();
            assertThat(token.split("\\.")).hasSize(3); // header.payload.signature
        }

        @Test
        void tokensConsecutivosParaMismoUsuarioSonIguales() {
            // Sin nbf/jti aleatorio y emitidos en el mismo instante de reloj,
            // el contenido del token es determinístico. Si en el futuro se agregan
            // claims aleatorios, este test debe relajarse.
            String t1 = jwtUtil.generateToken("juan01", 1L);
            String t2 = jwtUtil.generateToken("juan01", 1L);
            assertThat(t1).isEqualTo(t2);
        }

        @Test
        void tokensParaUsuariosDistintosSonDiferentes() {
            String t1 = jwtUtil.generateToken("juan01", 1L);
            String t2 = jwtUtil.generateToken("maria02", 2L);
            assertThat(t1).isNotEqualTo(t2);
        }

        @Test
        void payloadIncluyeUserIdComoClaim() {
            String token = jwtUtil.generateToken("juan01", 99L);

            // Decodificamos manualmente con la misma key para verificar el claim
            SecretKey key = Keys.hmacShaKeyFor(SECRET.getBytes(StandardCharsets.UTF_8));
            Claims claims = Jwts.parser().verifyWith(key).build()
                    .parseSignedClaims(token).getPayload();

            assertThat(claims.getSubject()).isEqualTo("juan01");
            assertThat(claims.get("userId", Integer.class)).isEqualTo(99);
            assertThat(claims.getIssuedAt()).isNotNull();
            assertThat(claims.getExpiration()).isAfter(claims.getIssuedAt());
        }
    }

    @Nested
    @DisplayName("validateToken / extractUsername")
    class Validate {

        @Test
        void tokenValidoEsAceptadoYExtraeUsername() {
            String token = jwtUtil.generateToken("juan01", 1L);
            assertThat(jwtUtil.validateToken(token)).isTrue();
            assertThat(jwtUtil.extractUsername(token)).isEqualTo("juan01");
        }

        @Test
        void tokenConSecretDiferenteEsRechazado() {
            JwtUtil otroSigner = new JwtUtil("otro-secreto-completamente-distinto-de-256-bits", ONE_DAY_MS, "");
            String tokenForaneo = otroSigner.generateToken("juan01", 1L);

            assertThat(jwtUtil.validateToken(tokenForaneo)).isFalse();
        }

        @Test
        void tokenMalformadoEsRechazadoSinExcepcion() {
            assertThat(jwtUtil.validateToken("no-es-un-jwt")).isFalse();
            assertThat(jwtUtil.validateToken("aaa.bbb.ccc")).isFalse();
            assertThat(jwtUtil.validateToken("")).isFalse();
        }

        @Test
        void tokenExpiradoEsRechazado() throws InterruptedException {
            JwtUtil shortLived = new JwtUtil(SECRET, 1L, ""); // 1ms de expiración
            String token = shortLived.generateToken("juan01", 1L);

            // Garantizamos que pase la ventana de expiración
            Thread.sleep(20);

            assertThat(shortLived.validateToken(token)).isFalse();
        }
    }

    @Nested
    @DisplayName("getExpirationMs")
    class Expiration {

        @Test
        void retornaElValorConfiguradoEnConstruccion() {
            assertThat(jwtUtil.getExpirationMs()).isEqualTo(ONE_DAY_MS);
            assertThat(new JwtUtil(SECRET, 60_000L, "").getExpirationMs()).isEqualTo(60_000L);
        }
    }

    @Nested
    @DisplayName("Hardening: secret obligatorio en perfil prod")
    class ProdHardening {

        @Test
        @DisplayName("perfil 'prod' + secret default → falla el arranque")
        void prodConDefaultSecretLanza() {
            org.junit.jupiter.api.Assertions.assertThrows(
                IllegalStateException.class,
                () -> new JwtUtil(JwtUtil.DEFAULT_DEV_SECRET, ONE_DAY_MS, "prod")
            );
        }

        @Test
        @DisplayName("perfil 'prod' + secret vacío → falla el arranque")
        void prodConSecretVacioLanza() {
            org.junit.jupiter.api.Assertions.assertThrows(
                IllegalStateException.class,
                () -> new JwtUtil("", ONE_DAY_MS, "prod")
            );
        }

        @Test
        @DisplayName("perfil combinado 'prod,monitoring' → también falla con default")
        void prodConCombinacionDePerfilesLanza() {
            org.junit.jupiter.api.Assertions.assertThrows(
                IllegalStateException.class,
                () -> new JwtUtil(JwtUtil.DEFAULT_DEV_SECRET, ONE_DAY_MS, "prod,monitoring")
            );
        }

        @Test
        @DisplayName("perfil 'prod' + secret robusto → arranca normal")
        void prodConSecretRobustoArranca() {
            JwtUtil jwt = new JwtUtil("super-secret-de-produccion-rotado-por-vault-256bits!!", ONE_DAY_MS, "prod");
            assertThat(jwt).isNotNull();
        }

        @Test
        @DisplayName("perfil 'dev' + secret default → arranca normal")
        void devConDefaultSecretArranca() {
            JwtUtil jwt = new JwtUtil(JwtUtil.DEFAULT_DEV_SECRET, ONE_DAY_MS, "dev");
            assertThat(jwt).isNotNull();
        }

        @Test
        @DisplayName("perfil vacío + secret default → arranca normal")
        void perfilVacioArranca() {
            JwtUtil jwt = new JwtUtil(JwtUtil.DEFAULT_DEV_SECRET, ONE_DAY_MS, "");
            assertThat(jwt).isNotNull();
        }
    }
}
