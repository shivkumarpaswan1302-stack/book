(() => {
  const modal = document.querySelector("#auth-modal");
  const message = document.querySelector("#auth-message");
  const state = { user: null, view: "login", phone: "" };

  function announce(text = "") {
    message.textContent = text;
    message.classList.toggle("has-message", Boolean(text));
  }

  function setView(view) {
    state.view = view;
    document.querySelectorAll("[data-auth-view]").forEach((section) => section.classList.toggle("is-hidden", section.dataset.authView !== view));
    const titles = { login: "Welcome back", signup: "Find your next story", phone: "Sign in with your phone", otp: "Check your messages", forgot: "Reset your password", reset: "Choose a new password" };
    document.querySelector("#auth-title").textContent = titles[view] || titles.login;
    announce("");
  }

  function open(view = "login") {
    setView(view);
    if (!modal.open) modal.showModal();
  }

  async function request(path, body) {
    const response = await fetch(path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const result = response.status === 204 ? null : await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = Array.isArray(result?.detail) ? result.detail.map((entry) => entry.msg).join(". ") : result?.detail;
      throw new Error(detail || "Something went wrong. Please try again.");
    }
    return result;
  }

  function setUser(user) {
    state.user = user || null;
    window.dispatchEvent(new CustomEvent("kahaniya:auth-change", { detail: { user: state.user } }));
  }

  async function submit(form, action) {
    const submitButton = form.querySelector("[type='submit']");
    submitButton.disabled = true;
    announce("One moment…");
    try {
      const result = await action(new FormData(form));
      if (result?.user) {
        setUser(result.user);
        modal.close();
        form.reset();
        announce("");
        return;
      }
      return result;
    } catch (error) {
      announce(error.message);
      return null;
    } finally {
      submitButton.disabled = false;
    }
  }

  function makePhone(formData) {
    const national = String(formData.get("phone") || "").replace(/\D/g, "").replace(/^0+/, "");
    return `${formData.get("country_code")}${national}`;
  }

  document.addEventListener("click", (event) => {
    const viewLink = event.target.closest("[data-auth-view-link]");
    if (viewLink) setView(viewLink.dataset.authViewLink);
    if (event.target.closest("#login-button")) open("login");
  });

  document.querySelector("#auth-login-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submit(event.currentTarget, (form) => request("/auth/login", { identifier: form.get("identifier"), password: form.get("password") }));
  });

  document.querySelector("#auth-signup-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submit(event.currentTarget, (form) => {
      const phone = form.get("phone") ? makePhone(form) : null;
      return request("/auth/register", { name: form.get("name"), email: form.get("email"), username: form.get("username"), phone_number: phone, password: form.get("password") });
    });
  });

  document.querySelector("#auth-phone-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submit(event.currentTarget, async (form) => {
      state.phone = makePhone(form);
      const result = await request("/auth/send-otp", { phone_number: state.phone });
      document.querySelector("#otp-destination").textContent = `Enter the verification code sent to ${state.phone}.`;
      setView("otp");
      if (result.development_code) {
        document.querySelector("#auth-otp-form [name='otp']").value = result.development_code;
        announce(`Development mode code: ${result.development_code}`);
      }
      return null;
    });
  });

  document.querySelector("#auth-otp-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submit(event.currentTarget, (form) => request("/auth/verify-otp", { phone_number: state.phone, otp: form.get("otp") }));
  });

  document.querySelector("#auth-forgot-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submit(event.currentTarget, async (form) => {
      const result = await request("/auth/forgot-password", { identifier: form.get("identifier") });
      if (result.development_reset_token) {
        document.querySelector("#auth-reset-form [name='reset_token']").value = result.development_reset_token;
        setView("reset");
        announce("Development mode: reset token generated for this request.");
      } else {
        announce(result.message);
      }
      return null;
    });
  });

  document.querySelector("#auth-reset-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submit(event.currentTarget, async (form) => {
      const result = await request("/auth/reset-password", { reset_token: form.get("reset_token"), new_password: form.get("new_password") });
      form.reset();
      setView("login");
      announce(result.message);
      return null;
    });
  });

  window.KahaniyaAuth = {
    open,
    get user() { return state.user; },
    async logout() {
      await request("/auth/logout", {});
      setUser(null);
    },
  };

  async function restoreSession() {
    try {
      const response = await fetch("/auth/me", { credentials: "same-origin" });
      if (response.ok) { setUser(await response.json()); return; }
      const refreshed = await fetch("/auth/refresh", { method: "POST", credentials: "same-origin" });
      if (refreshed.ok) {
        const result = await refreshed.json();
        setUser(result.user);
      }
    } catch {
      setUser(null);
    }
  }

  const resetToken = new URLSearchParams(window.location.search).get("reset_token");
  if (resetToken) {
    document.querySelector("#auth-reset-form [name='reset_token']").value = resetToken;
    open("reset");
    window.history.replaceState({}, "", window.location.pathname + window.location.hash);
  }
  restoreSession();
})();