/* Shared OTP-login client. Token kept in sessionStorage for this prototype; prefer an httpOnly cookie in production. */
window.Auth = (() => {
  let tok = null;
  try { tok = sessionStorage.getItem("ss_tok"); } catch (e) {}
  async function call(path, method = "GET", body) {
    const r = await fetch(path, { method, headers: { "Content-Type": "application/json", ...(tok ? { Authorization: "Bearer " + tok } : {}) }, body: body ? JSON.stringify(body) : undefined });
    if (r.status === 204) return null;
    const d = await r.json().catch(() => ({}));
    if (!r.ok) { if (r.status === 401 && tok) { logout(); } throw new Error(typeof d.detail === "string" ? d.detail : "Request failed (" + r.status + ")"); }
    return d;
  }
  function logout() { tok = null; try { sessionStorage.removeItem("ss_tok"); } catch (e) {} }
  return {
    get token() { return tok; }, call, logout,
    request: phone => call("/api/auth/otp/request", "POST", { phone }),
    async verify(phone, otp) { const d = await call("/api/auth/otp/verify", "POST", { phone, otp }); tok = d.token; try { sessionStorage.setItem("ss_tok", tok); } catch (e) {} return d; }
  };
})();
