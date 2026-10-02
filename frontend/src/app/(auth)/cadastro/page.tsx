"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { API } from "../../../lib/saas";

type FormState = {
  name: string;
  email: string;
  company_name: string;
  password: string;
  password_confirmation: string;
};

const initialForm: FormState = {
  name: "",
  email: "",
  company_name: "",
  password: "",
  password_confirmation: "",
};

async function readApiMessage(response: Response): Promise<{ access_token?: string; detail?: string }> {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

export default function Cadastro() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(initialForm);
  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    setMessage("");
    setSuccess("");

    const name = form.name.trim();
    const email = form.email.trim().toLowerCase();
    const companyName = form.company_name.trim();

    if (name.length < 2) {
      setMessage("Informe seu nome com pelo menos 2 caracteres.");
      return;
    }
    if (companyName.length < 2) {
      setMessage("Informe o nome da empresa/workspace.");
      return;
    }
    if (form.password.length < 8) {
      setMessage("A senha deve ter no mínimo 8 caracteres.");
      return;
    }
    if (form.password !== form.password_confirmation) {
      setMessage("As senhas não conferem. Digite a mesma senha nos dois campos.");
      return;
    }

    setSubmitting(true);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20000);

    try {
      const response = await fetch(`${API}/api/v1/saas/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          email,
          company_name: companyName,
          password: form.password,
        }),
        signal: controller.signal,
      });

      const data = await readApiMessage(response);
      if (!response.ok) {
        setMessage(data.detail || `Não foi possível criar o workspace (HTTP ${response.status}).`);
        return;
      }
      if (!data.access_token) {
        setMessage("O cadastro foi processado, mas a API não retornou a sessão de acesso.");
        return;
      }

      localStorage.setItem("ai_token", data.access_token);
      setSuccess("Workspace criado com sucesso. Abrindo o painel...");
      router.replace("/dashboard");
      router.refresh();
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setMessage("A API demorou mais de 20 segundos para responder. Verifique o backend e tente novamente.");
      } else {
        setMessage("Não foi possível conectar à API. Verifique a URL do backend, CORS e se o serviço Railway está online.");
      }
    } finally {
      window.clearTimeout(timeout);
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="card auth-card auth-card-wide">
        <Link href="/" className="auth-logo" aria-label="Voltar para a página inicial"><Image src="/ai-affiliate-logo.png" alt="AIAffiliateIntelligence" width={220} height={110} priority /></Link>
        <span className="eyebrow">COMECE SEU TRIAL</span>
        <h1>Crie sua empresa</h1>
        <p className="muted">14 dias para configurar seu workspace e validar o fluxo.</p>

        <form onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="name">Seu nome</label>
            <input id="name" autoComplete="name" value={form.name} onChange={(e) => update("name", e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="email">E-mail</label>
            <input id="email" type="email" autoComplete="email" value={form.email} onChange={(e) => update("email", e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="company_name">Empresa / workspace</label>
            <input id="company_name" autoComplete="organization" value={form.company_name} onChange={(e) => update("company_name", e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="password">Senha (mín. 8 caracteres)</label>
            <input id="password" type="password" autoComplete="new-password" minLength={8} value={form.password} onChange={(e) => update("password", e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="password_confirmation">Confirmar senha</label>
            <input id="password_confirmation" type="password" autoComplete="new-password" minLength={8} value={form.password_confirmation} onChange={(e) => update("password_confirmation", e.target.value)} required />
          </div>

          {message && <div className="alert" role="alert" style={{ marginTop: 14 }}>{message}</div>}
          {success && <div className="alert" role="status" style={{ marginTop: 14 }}>{success}</div>}

          <button className="btn primary" type="submit" disabled={submitting} style={{ marginTop: 16, width: "100%", opacity: submitting ? 0.7 : 1 }}>
            {submitting ? "Criando workspace..." : "Criar workspace"}
          </button>
        </form>

        <p className="muted auth-switch">Já possui uma conta? <Link href="/login">Entrar</Link></p>
      </section>
    </main>
  );
}
