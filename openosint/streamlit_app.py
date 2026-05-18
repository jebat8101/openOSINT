# openosint/streamlit_app.py
"""
OpenOSINT Streamlit web interface.

Run:
    streamlit run openosint/streamlit_app.py
    # or after install:
    openosint-web
"""

from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

import streamlit as st

from openosint.agent import AgentResponse, OllamaAgent, OpenOSINTAgent
from openosint.json_output import format_tool_result
from openosint.tools.generate_dorks import run_dork_osint
from openosint.tools.search_breach import run_breach_osint
from openosint.tools.search_domain import run_domain_osint
from openosint.tools.search_email import run_email_osint
from openosint.tools.search_ip import run_ip_osint
from openosint.tools.search_paste import run_paste_osint
from openosint.tools.search_phone import run_phone_osint
from openosint.tools.search_shodan import run_shodan_osint
from openosint.tools.search_username import run_username_osint
from openosint.tools.search_virustotal import run_virustotal_osint
from openosint.tools.search_whois import run_whois_osint

# ---------------------------------------------------------------------------
# Tool registry (direct mode — no AI credits required)
# ---------------------------------------------------------------------------

ToolRunner = Callable[[str], Coroutine[Any, Any, str]]

_TOOLS: dict[str, dict[str, Any]] = {
    "Email (holehe)": {
        "id": "search_email",
        "param": "email",
        "placeholder": "target@example.com",
        "run": lambda t: run_email_osint(email=t, timeout_seconds=120),
        "bundle": "email",
    },
    "Username (sherlock)": {
        "id": "search_username",
        "param": "username",
        "placeholder": "johndoe99",
        "run": lambda t: run_username_osint(username=t, timeout_seconds=180),
        "bundle": "username",
    },
    "Breach (HIBP)": {
        "id": "search_breach",
        "param": "email",
        "placeholder": "target@example.com",
        "run": lambda t: run_breach_osint(email=t),
    },
    "Domain / subdomains": {
        "id": "search_domain",
        "param": "domain",
        "placeholder": "example.com",
        "run": lambda t: run_domain_osint(domain=t, timeout_seconds=120),
    },
    "WHOIS": {
        "id": "search_whois",
        "param": "domain",
        "placeholder": "example.com",
        "run": lambda t: run_whois_osint(domain=t, timeout_seconds=15),
    },
    "IP lookup": {
        "id": "search_ip",
        "param": "ip",
        "placeholder": "8.8.8.8",
        "run": lambda t: run_ip_osint(ip=t, timeout_seconds=10),
    },
    "Google dorks": {
        "id": "generate_dorks",
        "param": "target",
        "placeholder": "name, email, or domain",
        "run": lambda t: run_dork_osint(target=t),
    },
    "Pastebin search": {
        "id": "search_paste",
        "param": "query",
        "placeholder": "email or username",
        "run": lambda t: run_paste_osint(query=t, timeout_seconds=15),
    },
    "Phone (phoneinfoga)": {
        "id": "search_phone",
        "param": "phone",
        "placeholder": "+14155552671",
        "run": lambda t: run_phone_osint(phone=t, timeout_seconds=60),
    },
    "Shodan": {
        "id": "search_shodan",
        "param": "query",
        "placeholder": "8.8.8.8 or port:443",
        "run": lambda t: run_shodan_osint(query=t, timeout_seconds=30),
        "needs_key": "SHODAN_API_KEY",
    },
    "VirusTotal": {
        "id": "search_virustotal",
        "param": "target",
        "placeholder": "IP, domain, URL, or hash",
        "run": lambda t: run_virustotal_osint(target=t, timeout_seconds=30),
        "needs_key": "VIRUSTOTAL_API_KEY",
    },
}

_BUNDLE_EXTRA: dict[str, tuple[str, ToolRunner]] = {
    "email": ("search_breach", lambda t: run_breach_osint(email=t)),
    "username": ("search_paste", lambda t: run_paste_osint(query=t, timeout_seconds=15)),
}

_CSS = """
<style>
    .stApp { background: linear-gradient(165deg, #0a0f1a 0%, #111827 45%, #0d1117 100%); }
    h1, h2, h3 { color: #00ff88 !important; font-weight: 700 !important; }
    [data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #1e293b; }
    .osint-badge {
        display: inline-block; padding: 0.2rem 0.6rem; border-radius: 6px;
        background: #00ff8822; color: #00ff88; font-size: 0.75rem; font-weight: 600;
        border: 1px solid #00ff8844; margin-bottom: 0.5rem;
    }
    .osint-disclaimer { color: #94a3b8; font-size: 0.8rem; line-height: 1.4; }
</style>
"""


def _run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    return asyncio.run(coro)


def _apply_sidebar_env() -> None:
    """Push sidebar secrets into os.environ for tool modules."""
    mapping = {
        "anthropic_key": "ANTHROPIC_API_KEY",
        "shodan_key": "SHODAN_API_KEY",
        "vt_key": "VIRUSTOTAL_API_KEY",
        "hibp_key": "HIBP_API_KEY",
        "ipinfo_key": "IPINFO_TOKEN",
    }
    for session_key, env_key in mapping.items():
        val = st.session_state.get(session_key, "").strip()
        if val:
            os.environ[env_key] = val


def _agent_signature() -> tuple[Any, ...]:
    return (
        st.session_state.get("provider", "anthropic"),
        st.session_state.get("ollama_model", "llama3.2"),
        st.session_state.get("ollama_host", "http://localhost:11434"),
        st.session_state.get("anthropic_key", "").strip(),
    )


def _build_agent() -> OpenOSINTAgent | OllamaAgent:
    provider = st.session_state.get("provider", "anthropic")
    if provider == "ollama":
        return OllamaAgent(
            model=st.session_state.get("ollama_model", "llama3.2"),
            host=st.session_state.get("ollama_host", "http://localhost:11434"),
        )
    key = st.session_state.get("anthropic_key", "").strip()
    return OpenOSINTAgent(api_key=key or None)


def _get_agent() -> OpenOSINTAgent | OllamaAgent:
    sig = _agent_signature()
    if st.session_state.get("_agent_sig") != sig:
        st.session_state.agent = _build_agent()
        st.session_state._agent_sig = sig
    return st.session_state.agent


def _render_tool_result(label: str, text: str) -> None:
    st.markdown(f'<span class="osint-badge">{label}</span>', unsafe_allow_html=True)
    if text.strip().lower().startswith("scan error") or text.strip().lower().startswith("internal error"):
        st.error(text)
    else:
        st.code(text, language=None)


async def _run_tool_bundle(tool_label: str, target: str, parallel: bool) -> list[tuple[str, str]]:
    spec = _TOOLS[tool_label]
    primary_id = spec["id"]
    bundle = spec.get("bundle")

    if bundle and bundle in _BUNDLE_EXTRA and parallel:
        extra_id, extra_run = _BUNDLE_EXTRA[bundle]
        primary, extra_out = await asyncio.gather(spec["run"](target), extra_run(target))
        return [(primary_id, primary), (extra_id, extra_out)]

    primary = await spec["run"](target)
    rows: list[tuple[str, str]] = [(primary_id, primary)]
    if bundle and bundle in _BUNDLE_EXTRA:
        extra_id, extra_run = _BUNDLE_EXTRA[bundle]
        extra_out = await extra_run(target)
        rows.append((extra_id, extra_out))
    return rows


def _page_tools() -> None:
    st.subheader("Direct OSINT tools")
    st.caption("Run scanners without AI — no Anthropic credits required.")

    tool_label = st.selectbox("Tool", list(_TOOLS.keys()))
    spec = _TOOLS[tool_label]
    param = spec["param"]

    col1, col2 = st.columns([3, 1])
    with col1:
        target = st.text_input(
            param.replace("_", " ").title(),
            placeholder=spec["placeholder"],
            key="tool_target",
        )
    with col2:
        parallel = st.checkbox(
            "Parallel bundle",
            value=True,
            help="Email → + breach; Username → + paste",
            disabled=spec.get("bundle") is None,
        )

    needs = spec.get("needs_key")
    key_field = "shodan_key" if needs == "SHODAN_API_KEY" else "vt_key"
    if needs and not os.environ.get(needs) and not st.session_state.get(key_field, ""):
        st.warning(f"Set **{needs}** in the sidebar for this tool.")

    if st.button("Run scan", type="primary", use_container_width=True):
        if not target.strip():
            st.warning("Enter a target first.")
            return
        with st.spinner(f"Running {tool_label}…"):
            rows = _run_async(_run_tool_bundle(tool_label, target.strip(), parallel))

        st.session_state["last_tool_json"] = [
            format_tool_result(tid, target.strip(), out) for tid, out in rows
        ]
        for tid, out in rows:
            _render_tool_result(tid, out)

    if st.session_state.get("last_tool_json"):
        st.download_button(
            "Download JSON",
            data=json.dumps(st.session_state["last_tool_json"], indent=2),
            file_name=f"openosint_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )


def _page_agent() -> None:
    st.subheader("AI investigator")
    st.caption("Natural-language OSINT — Claude or local Ollama orchestrates the tools.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            for tc in msg.get("tool_calls", []):
                with st.expander(f"🔧 {tc['name']}", expanded=False):
                    st.json(tc.get("input", {}))
                    st.code(tc.get("result", ""), language=None)

    prompt = st.chat_input("Investigate a target or ask a question…")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            agent = _get_agent()
            response: AgentResponse = _run_async(agent.run(prompt))

        if response.error:
            st.error(response.error)
            st.session_state.messages.append(
                {"role": "assistant", "content": f"**Error:** {response.error}"}
            )
            return

        tool_payload = [
            {
                "name": tc.name,
                "input": tc.input,
                "result": tc.result[:8000] if tc.result else "",
            }
            for tc in response.tool_calls
        ]
        if response.content:
            st.markdown(response.content)
        for tc in tool_payload:
            with st.expander(f"🔧 {tc['name']}", expanded=False):
                st.json(tc.get("input", {}))
                st.code(tc.get("result", ""), language=None)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response.content or "_Tools executed — see expanders above._",
                "tool_calls": tool_payload,
            }
        )

    if st.button("Clear chat"):
        st.session_state.messages = []
        if "agent" in st.session_state:
            st.session_state.agent.clear_history()
        st.rerun()


def _init_session() -> None:
    defaults = {
        "provider": "anthropic",
        "ollama_model": "llama3.2",
        "ollama_host": "http://localhost:11434",
        "anthropic_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "shodan_key": os.environ.get("SHODAN_API_KEY", ""),
        "vt_key": os.environ.get("VIRUSTOTAL_API_KEY", ""),
        "hibp_key": os.environ.get("HIBP_API_KEY", ""),
        "ipinfo_key": os.environ.get("IPINFO_TOKEN", ""),
        "messages": [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def main() -> None:
    st.set_page_config(
        page_title="OpenOSINT",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    _init_session()

    with st.sidebar:
        st.markdown("## OpenOSINT")
        st.markdown(
            '<p class="osint-disclaimer">Authorized security research only. '
            "Use responsibly and comply with applicable laws.</p>",
            unsafe_allow_html=True,
        )
        st.divider()
        st.markdown("### AI provider")
        st.session_state.provider = st.radio(
            "Provider",
            ["anthropic", "ollama"],
            format_func=lambda x: "Anthropic (Claude)" if x == "anthropic" else "Ollama (local)",
            horizontal=True,
        )
        if st.session_state.provider == "anthropic":
            st.session_state.anthropic_key = st.text_input(
                "Anthropic API key",
                type="password",
                value=st.session_state.anthropic_key,
                help="console.anthropic.com",
            )
        else:
            st.session_state.ollama_host = st.text_input(
                "Ollama host", value=st.session_state.ollama_host
            )
            st.session_state.ollama_model = st.text_input(
                "Ollama model", value=st.session_state.ollama_model
            )

        st.divider()
        st.markdown("### API keys (optional)")
        st.session_state.shodan_key = st.text_input(
            "Shodan", type="password", value=st.session_state.shodan_key
        )
        st.session_state.vt_key = st.text_input(
            "VirusTotal", type="password", value=st.session_state.vt_key
        )
        st.session_state.hibp_key = st.text_input(
            "HIBP", type="password", value=st.session_state.hibp_key
        )
        st.session_state.ipinfo_key = st.text_input(
            "ipinfo.io", type="password", value=st.session_state.ipinfo_key
        )
        _apply_sidebar_env()

        st.divider()
        st.markdown(
            "[GitHub](https://github.com/OpenOSINT/OpenOSINT) · "
            "CLI: `openosint`"
        )

    st.title("🔍 OpenOSINT")
    st.markdown(
        "AI-powered OSINT — investigate emails, usernames, domains, and more."
    )

    tab_tools, tab_agent = st.tabs(["🛠 Tools (no AI)", "🤖 AI investigator"])

    with tab_tools:
        _page_tools()
    with tab_agent:
        _page_agent()


def main_web() -> None:
    """Entry point for `openosint-web` — launches Streamlit."""
    import sys
    from pathlib import Path

    import streamlit.web.cli as stcli

    app_path = str(Path(__file__).resolve())
    sys.argv = ["streamlit", "run", app_path, "--server.headless", "true", *sys.argv[1:]]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
