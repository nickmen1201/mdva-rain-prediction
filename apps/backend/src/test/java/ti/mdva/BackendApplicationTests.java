package ti.mdva;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

/**
 * Integration tests for the BackendApplication.
 * <p>
 * Verifies that the Spring application context loads correctly.
 *
 * @author MDVA Team
 * @version 1.0
 */
@SpringBootTest
@ActiveProfiles("test")
class BackendApplicationTests {

    /**
     * Verifies that the Spring application context loads without errors.
     */
    @Test
    void contextLoads() {
        // Context loads successfully if no exception is thrown
    }
}
