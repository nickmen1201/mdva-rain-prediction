package ti.mdva.service.impl;

import lombok.extern.slf4j.Slf4j;
import org.jooq.DSLContext;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import ti.mdva.model.dto.AuthResponseDTO;
import ti.mdva.model.dto.LoginRequestDTO;
import ti.mdva.model.dto.RegisterRequestDTO;
import ti.mdva.security.JwtUtil;
import ti.mdva.service.AuthService;

import static ti.mdva.jooq.Tables.USUARIOS;

@Slf4j
@Service
public class AuthServiceImpl implements AuthService {

    private final DSLContext dsl;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    public AuthServiceImpl(DSLContext dsl, PasswordEncoder passwordEncoder, JwtUtil jwtUtil) {
        this.dsl = dsl;
        this.passwordEncoder = passwordEncoder;
        this.jwtUtil = jwtUtil;
    }

    @Override
    public AuthResponseDTO register(RegisterRequestDTO request) {
        // Check for existing username or email
        boolean exists = dsl.fetchExists(
                dsl.selectFrom(USUARIOS)
                   .where(USUARIOS.USERNAME.eq(request.getUsername())
                      .or(USUARIOS.EMAIL.eq(request.getEmail())))
        );

        if (exists) {
            throw new IllegalArgumentException("Username or email already exists");
        }

        String hash = passwordEncoder.encode(request.getPassword());

        var record = dsl.insertInto(USUARIOS)
                .set(USUARIOS.NOMBRE, request.getNombre())
                .set(USUARIOS.USERNAME, request.getUsername())
                .set(USUARIOS.EMAIL, request.getEmail())
                .set(USUARIOS.AUTHHASH, hash)
                .set(USUARIOS.FECHA_NACIMIENTO, request.getFechaNacimiento())
                .set(USUARIOS.ID_BARRIO, request.getIdBarrio())
                .returning(USUARIOS.ID, USUARIOS.USERNAME, USUARIOS.EMAIL)
                .fetchOne();

        String token = jwtUtil.generateToken(record.getUsername(), record.getId());

        log.info("User registered: {}", record.getUsername());

        return AuthResponseDTO.builder()
                .token(token)
                .username(record.getUsername())
                .email(record.getEmail())
                .expiresIn(jwtUtil.getExpirationMs())
                .build();
    }

    @Override
    public AuthResponseDTO login(LoginRequestDTO request) {
        var user = dsl.selectFrom(USUARIOS)
                .where(USUARIOS.USERNAME.eq(request.getUsername()))
                .fetchOne();

        if (user == null || user.getAuthhash() == null
                || !passwordEncoder.matches(request.getPassword(), user.getAuthhash())) {
            throw new BadCredentialsException("Invalid username or password");
        }

        String token = jwtUtil.generateToken(user.getUsername(), user.getId());

        log.info("User logged in: {}", user.getUsername());

        return AuthResponseDTO.builder()
                .token(token)
                .username(user.getUsername())
                .email(user.getEmail())
                .expiresIn(jwtUtil.getExpirationMs())
                .build();
    }
}
