if (getAuth()) location.replace("index.html");

async function authRequest(path, payload, errorBox) {
  errorBox.classList.add("d-none");
  try {
    const data = await apiFetch(path, { method: "POST", body: JSON.stringify(payload) });
    localStorage.setItem("auth", JSON.stringify(data));
    location.href = "index.html";
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.classList.remove("d-none");
  }
}

document.getElementById("login-form").addEventListener("submit", (e) => {
  e.preventDefault();
  authRequest(
    "/auth/login",
    {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    },
    document.getElementById("login-error")
  );
});

document.getElementById("register-form").addEventListener("submit", (e) => {
  e.preventDefault();
  authRequest(
    "/auth/register",
    {
      full_name: document.getElementById("register-name").value,
      email: document.getElementById("register-email").value,
      faculty: document.getElementById("register-faculty").value || null,
      password: document.getElementById("register-password").value,
    },
    document.getElementById("register-error")
  );
});