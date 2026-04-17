package ti.mdva.service;

import ti.mdva.model.dto.AuthResponseDTO;
import ti.mdva.model.dto.LoginRequestDTO;
import ti.mdva.model.dto.RegisterRequestDTO;

public interface AuthService {
    AuthResponseDTO register(RegisterRequestDTO request);
    AuthResponseDTO login(LoginRequestDTO request);
}
