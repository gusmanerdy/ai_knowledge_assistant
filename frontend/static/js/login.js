const form = document.querySelector("#login-form");
const message = document.querySelector("#login-message");
const passwordInput = document.querySelector("#password");
const togglePassword = document.querySelector("#toggle-password");

togglePassword.addEventListener("click", () => {
    const shouldShow = passwordInput.type === "password";
    passwordInput.type = shouldShow ? "text" : "password";
    togglePassword.textContent = shouldShow ? "Sembunyikan" : "Lihat";
    togglePassword.setAttribute("aria-label", shouldShow ? "Sembunyikan password" : "Tampilkan password");
});

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = form.querySelector("button[type='submit']");
    message.hidden = true;
    submitButton.disabled = true;
    submitButton.textContent = "Memeriksa...";

    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: form.elements.username.value.trim(),
                password: form.elements.password.value,
            }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.detail || "Login gagal. Silakan coba lagi.");
        }
        window.location.replace(data.redirect_to || "/");
    } catch (error) {
        message.textContent = error.message;
        message.hidden = false;
        submitButton.disabled = false;
        submitButton.textContent = "Masuk";
    }
});
