
document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    const status = document.getElementById("authStatus");

    const API = {
        login: "/auth/login",
        register: "/auth/register"
    };

    function showStatus(message, success = false) {
        if (!status) return;

        status.textContent = message;
        status.style.color = success ? "#5bd6a5" : "#ff8d8d";
    }

    async function submitRequest(url, body) {
        const response = await fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body)
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(
                data.message || data.error || data.msg || `Request failed (${response.status}).`
            );
        }

        return data;
    }

    // LOGIN
    if (loginForm) {
        loginForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const button = document.getElementById("loginButton");

            if (button) {
                button.disabled = true;
                button.textContent = "Signing in...";
            }

            showStatus("");

            try {
                const email = document.getElementById("email").value.trim();
                const password = document.getElementById("password").value;

                const data = await submitRequest(API.login, {
                    email,
                    password
                });

                if (!data.access_token) {
                    throw new Error("No login token was returned by the server.");
                }

                localStorage.setItem("access_token", data.access_token);

                showStatus("Login successful! Opening your assistant...", true);

                window.location.href = "/chat";

            } catch (error) {
                console.error("Login error:", error);
                showStatus(error.message || "Unable to connect to the server.");

                if (button) {
                    button.disabled = false;
                    button.innerHTML = 'Sign in <span>→</span>';
                }
            }
        });
    }

    // REGISTER
    if (registerForm) {
        registerForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const button = document.getElementById("registerButton");

            if (button) {
                button.disabled = true;
                button.textContent = "Creating account...";
            }

            showStatus("");

            try {
                const username = document.getElementById("username").value.trim();
                const email = document.getElementById("email").value.trim();
                const password = document.getElementById("password").value;
                const confirmPassword = document.getElementById("confirmPassword").value;

                if (password !== confirmPassword) {
                    throw new Error("Passwords do not match.");
                }

                if (password.length < 8) {
                    throw new Error("Password must contain at least 8 characters.");
                }

                const data = await submitRequest(API.register, {
                    username,
                    email,
                    password
                });

                if (!data.access_token) {
                    throw new Error("Registration succeeded, but no login token was returned.");
                }

                localStorage.setItem("access_token", data.access_token);

                showStatus("Account created! Opening your assistant...", true);

                window.location.href = "/chat";

            } catch (error) {
                console.error("Registration error:", error);
                showStatus(error.message || "Unable to connect to the server.");

                if (button) {
                    button.disabled = false;
                    button.innerHTML = 'Create account <span>→</span>';
                }
            }
        });
    }
});
