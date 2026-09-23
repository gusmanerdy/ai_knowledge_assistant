async function loadSession() {
    try {
        const response = await fetch("/auth/me");
        if (!response.ok) {
            window.location.replace("/login");
            return;
        }
        const user = await response.json();
        document.querySelectorAll("[data-user-name]").forEach((element) => {
            element.textContent = user.display_name;
            element.title = `Role: ${user.role}`;
        });
        document.querySelectorAll("[data-role]").forEach((element) => {
            const roles = element.dataset.role.split(",");
            element.hidden = !roles.includes(user.role);
        });
    } catch {
        window.location.replace("/login");
    }
}

document.querySelectorAll("[data-logout]").forEach((button) => {
    button.addEventListener("click", async () => {
        button.disabled = true;
        try {
            await fetch("/auth/logout", { method: "POST" });
        } finally {
            window.location.replace("/login");
        }
    });
});

loadSession();
