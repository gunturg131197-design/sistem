import React, { useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";

export default function AuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = location.hash || window.location.hash;
    const params = new URLSearchParams(hash.replace(/^#/, ""));
    const sessionId = params.get("session_id");

    if (!sessionId) {
      navigate("/login", { replace: true });
      return;
    }

    (async () => {
      try {
        const { data } = await api.post("/auth/session", { session_id: sessionId });
        setUser(data);
        window.history.replaceState({}, document.title, "/");
        toast.success(`Selamat datang, ${data.name}`);
        navigate("/", { replace: true, state: { user: data } });
      } catch (e) {
        toast.error("Login gagal. Coba lagi.");
        navigate("/login", { replace: true });
      }
    })();
  }, [location.hash, navigate, setUser]);

  return (
    <div className="min-h-screen bg-background grid-bg flex items-center justify-center">
      <div className="text-center">
        <div className="h-1 w-24 bg-primary mx-auto mb-6 animate-pulse" />
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground" data-testid="auth-callback-loading">
          Establishing secure session…
        </p>
      </div>
    </div>
  );
}
