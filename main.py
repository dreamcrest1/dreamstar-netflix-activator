import os
import json
from fastapi import FastAPI, Request, Body, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from sheet_manager import fetch_and_validate_user, DEFAULT_SHEET_URL
from profile_manager import (
    get_all_profiles, add_or_update_profile, delete_profile,
    get_profile_cookies, parse_cookies, export_profiles_b64
)
from data_manager import (
    get_settings, update_settings, log_activation,
    check_activation_limit, get_activation_stats, export_full_state_b64,
    record_pageview, toggle_block_number, get_blocked_numbers,
    get_debug_logs, clear_debug_logs
)
from activation_engine import activate_tv

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "StarAdmin999")

app = FastAPI(title="Dreamstar Solutions - Netflix TV Matrix")

# Brand New Cyber-Industrial Deep Slate UI
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dreamstar Solutions | Netflix TV Activator</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@400;600;700&family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        brand: {
                            cyan: '#00f2fe',
                            blue: '#4facfe',
                            dark: '#070b12',
                            panel: '#0d1524',
                            border: '#1b2842',
                            glow: 'rgba(0, 242, 254, 0.15)'
                        }
                    },
                    fontFamily: {
                        cyber: ['"Chakra Petch"', 'sans-serif'],
                        sans: ['"Space Grotesk"', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace']
                    }
                }
            }
        }
    </script>
    <style>
        body { background-color: #05080e; background-image: radial-gradient(circle at 50% 0%, #0f1e38 0%, #05080e 70%); }
        .cyber-card { background: rgba(13, 21, 36, 0.85); backdrop-filter: blur(14px); border: 1px solid #1b2842; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6); }
        .cyber-card:hover { border-color: rgba(0, 242, 254, 0.35); }
        .neon-glow { box-shadow: 0 0 25px rgba(0, 242, 254, 0.25); }
        .glow-text { text-shadow: 0 0 15px rgba(0, 242, 254, 0.5); }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: #070b12; }
        ::-webkit-scrollbar-thumb { background: #1b2842; border-radius: 4px; }
    </style>
</head>
<body class="text-slate-200 min-h-screen flex flex-col justify-between p-3 md:p-6 font-sans antialiased relative pb-24">

    <!-- Top Navigation Header -->
    <header class="max-w-3xl mx-auto w-full flex justify-between items-center cyber-card rounded-2xl p-4 mb-6 border-brand-border">
        <div class="flex items-center gap-3">
            <div class="w-11 h-11 rounded-xl bg-gradient-to-tr from-brand-cyan to-brand-blue flex items-center justify-center text-black font-black text-xl shadow-lg shadow-cyan-500/30">
                <i class="fa-solid fa-star"></i>
            </div>
            <div>
                <h1 class="text-lg md:text-xl font-cyber font-bold tracking-wide text-white flex items-center gap-2">
                    DREAMSTAR <span class="text-brand-cyan glow-text">SOLUTIONS</span>
                </h1>
                <p class="text-[11px] font-mono text-slate-400">TV Activation Gateway • Instant Subscription Connect</p>
            </div>
        </div>
        <a href="/admin" class="bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-brand-cyan px-3.5 py-2 rounded-xl text-xs font-mono font-semibold transition border border-brand-border flex items-center gap-2">
            <i class="fa-solid fa-sliders text-brand-cyan"></i>
            <span>Admin</span>
        </a>
    </header>

    <main class="max-w-3xl mx-auto w-full space-y-5">

        <!-- Announcement Banner -->
        <div class="cyber-card rounded-2xl p-4 md:p-5 flex flex-col md:flex-row justify-between items-center gap-4 border-l-4 border-l-brand-cyan">
            <div class="flex items-center gap-3">
                <div class="bg-brand-cyan/10 border border-brand-cyan/30 text-brand-cyan w-10 h-10 rounded-xl flex items-center justify-center text-lg">
                    <i class="fa-solid fa-satellite-dish"></i>
                </div>
                <div>
                    <div class="text-[11px] font-mono uppercase text-brand-cyan tracking-wider font-semibold">Dreamstar Direct Service</div>
                    <div class="text-sm md:text-base font-bold text-white">Buy or Renew Ultra HD 4K Streaming Access</div>
                </div>
            </div>
            <a href="https://wa.me/919991483279?text=Hi%20Dreamstar%20Solutions%2C%20I%20want%20to%20buy%20or%20renew%20Netflix%20UHD%20Access" target="_blank"
               class="bg-gradient-to-r from-brand-cyan to-brand-blue hover:brightness-110 text-black font-bold px-5 py-2.5 rounded-xl text-xs md:text-sm font-cyber uppercase tracking-wider transition flex items-center gap-2 shadow-lg shadow-cyan-500/20">
                <i class="fa-brands fa-whatsapp text-base"></i>
                <span>Order On WhatsApp</span>
            </a>
        </div>

        <!-- Global Message Strip -->
        <div id="statusStrip" class="hidden rounded-xl p-4 text-xs md:text-sm font-medium flex items-center gap-3 border transition-all"></div>

        <!-- STEP 1: Phone Validation -->
        <div class="cyber-card rounded-2xl p-5 md:p-6 space-y-4">
            <div class="flex justify-between items-center border-b border-brand-border/60 pb-3">
                <div class="flex items-center gap-2.5">
                    <span class="w-6 h-6 rounded-lg bg-brand-cyan/10 border border-brand-cyan/30 text-brand-cyan text-xs font-mono font-bold flex items-center justify-center">01</span>
                    <h2 class="text-sm md:text-base font-cyber font-bold text-white tracking-wide">VERIFY SUBSCRIBER MOBILE</h2>
                </div>
                <span id="badgeStep1" class="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">AWAITING INPUT</span>
            </div>

            <form id="verifyForm" onsubmit="onVerifyUser(event)" class="space-y-4">
                <div>
                    <label class="block text-xs font-mono uppercase text-slate-400 mb-2">Registered 10-Digit Phone Number</label>
                    <div class="relative">
                        <span class="absolute left-4 top-3 text-slate-500 font-mono text-sm font-bold">+91</span>
                        <input type="tel" id="mobileInput" placeholder="Enter registered phone number" maxlength="10" required
                               class="w-full bg-slate-950/80 border border-brand-border rounded-xl py-3 pl-14 pr-4 text-white text-lg font-mono tracking-widest focus:outline-none focus:border-brand-cyan transition">
                    </div>
                </div>

                <button type="submit" id="btnVerify" class="w-full bg-slate-900 hover:bg-slate-800 border border-brand-border hover:border-brand-cyan/50 text-white font-cyber font-bold py-3.5 rounded-xl transition flex items-center justify-center gap-2 text-sm tracking-wider">
                    <i class="fa-solid fa-fingerprint text-brand-cyan"></i>
                    <span>VERIFY SUBSCRIBER RECORD</span>
                </button>
            </form>

            <div id="profileCard" class="hidden bg-slate-950/90 border border-cyan-900/40 rounded-xl p-4 space-y-2">
                <div class="flex justify-between items-center text-xs">
                    <span class="text-slate-400 font-mono">Assigned Profile:</span>
                    <span id="displayEmail" class="text-brand-cyan font-mono font-bold">--</span>
                </div>
                <div class="flex justify-between items-center text-xs">
                    <span class="text-slate-400 font-mono">Subscription Expiry:</span>
                    <span id="displayExpiry" class="text-emerald-400 font-mono">--</span>
                </div>
            </div>
        </div>

        <!-- STEP 2: Code Activation -->
        <div id="activationBox" class="cyber-card rounded-2xl p-5 md:p-6 space-y-4 opacity-40 pointer-events-none transition-all duration-300">
            <div class="flex justify-between items-center border-b border-brand-border/60 pb-3">
                <div class="flex items-center gap-2.5">
                    <span class="w-6 h-6 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono font-bold flex items-center justify-center">02</span>
                    <h2 class="text-sm md:text-base font-cyber font-bold text-white tracking-wide">INPUT 8-DIGIT TV CODE</h2>
                </div>
                <span class="text-[10px] font-mono text-slate-500">netflix.com/tv2</span>
            </div>

            <form id="activateForm" onsubmit="onActivateTV(event)" class="space-y-4">
                <div>
                    <label class="block text-xs font-mono uppercase text-slate-400 mb-2">Code displayed on your television</label>
                    <input type="text" id="tvCodeInput" placeholder="● ● ● ●   ● ● ● ●" maxlength="8" required
                           class="w-full bg-slate-950/80 border border-brand-border rounded-xl py-3.5 px-4 text-center text-2xl font-mono tracking-widest text-brand-cyan uppercase focus:outline-none focus:border-brand-cyan transition font-bold">
                </div>

                <button type="submit" id="btnActivate" class="w-full bg-gradient-to-r from-brand-cyan via-teal-400 to-emerald-400 hover:brightness-110 text-black font-cyber font-bold py-4 rounded-xl transition flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 text-base tracking-wider">
                    <i class="fa-solid fa-tv"></i>
                    <span>CONNECT TELEVISION NOW</span>
                </button>
            </form>
        </div>

        <!-- Terminal Console -->
        <div class="cyber-card rounded-2xl p-4 md:p-5 space-y-2">
            <div class="flex justify-between items-center">
                <div class="text-[10px] font-mono uppercase text-slate-400 flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    Terminal Execution Log
                </div>
                <button onclick="clearConsole()" class="text-[10px] font-mono text-slate-500 hover:text-slate-300">CLEAR</button>
            </div>
            <div id="telemetryConsole" class="bg-black/90 border border-slate-900 text-emerald-400 font-mono text-xs p-3.5 rounded-xl h-28 overflow-y-auto space-y-1">
                <div>[SYSTEM READY] Enter verified 10-digit mobile number to initiate.</div>
            </div>
        </div>

        <!-- Formatted Result Card -->
        <div id="outputBox" class="hidden cyber-card rounded-2xl p-5 md:p-6 space-y-3 border-emerald-500/40">
            <div class="text-xs font-mono uppercase text-emerald-400 flex items-center gap-2 font-bold">
                <i class="fa-solid fa-circle-check"></i>
                TV Activation Completed
            </div>
            <textarea id="outputText" readonly rows="8" class="w-full bg-slate-950/90 border border-slate-800 rounded-xl p-3.5 text-xs text-slate-300 font-mono focus:outline-none resize-none"></textarea>
            <button onclick="copyOutputText()" id="btnCopy" class="w-full bg-slate-800 hover:bg-slate-700 text-white font-mono font-bold py-3 rounded-xl transition flex items-center justify-center gap-2 text-xs uppercase tracking-wider">
                <i class="fa-solid fa-copy text-brand-cyan"></i>
                <span>Copy Summary To Clipboard</span>
            </button>
        </div>

    </main>

    <!-- Floating WhatsApp Help Button -->
    <a href="https://wa.me/919991483279?text=Hi%20Dreamstar%20Solutions%2C%20I%20need%20help%20with%20TV%20Activation" target="_blank"
       class="fixed bottom-5 right-5 bg-gradient-to-r from-emerald-500 to-teal-500 hover:brightness-110 text-black font-bold px-4 py-3 rounded-full shadow-2xl flex items-center gap-2.5 z-40 transition transform hover:scale-105 border border-emerald-300/40 font-mono text-xs">
        <i class="fa-brands fa-whatsapp text-xl text-black"></i>
        <span>WhatsApp Support</span>
    </a>

    <script>
        let verifiedMobile = null;
        let assignedEmail = null;

        function logTelemetry(msg, level="INFO") {
            const time = new Date().toLocaleTimeString();
            const box = document.getElementById('telemetryConsole');
            const row = document.createElement('div');
            const colorClass = level === 'ERROR' ? 'text-rose-400' : level === 'SUCCESS' ? 'text-emerald-400' : 'text-slate-300';
            row.innerHTML = `<span class="text-slate-600">[${time}]</span> <span class="${colorClass}">[${level}] ${msg}</span>`;
            box.appendChild(row);
            box.scrollTop = box.scrollHeight;
        }

        function clearConsole() {
            document.getElementById('telemetryConsole').innerHTML = '';
        }

        function showMessageStrip(type, msg) {
            const el = document.getElementById('statusStrip');
            el.classList.remove('hidden', 'bg-rose-950/70', 'border-rose-800', 'text-rose-300', 'bg-emerald-950/70', 'border-emerald-800', 'text-emerald-300');
            if (type === 'error') {
                el.classList.add('bg-rose-950/70', 'border-rose-800', 'text-rose-300');
                el.innerHTML = `<i class="fa-solid fa-triangle-exclamation text-rose-400"></i> <span>${msg}</span>`;
            } else {
                el.classList.add('bg-emerald-950/70', 'border-emerald-800', 'text-emerald-300');
                el.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400"></i> <span>${msg}</span>`;
            }
        }

        async function fetchWithTimeout(resource, options = {}) {
            const { timeout = 65000 } = options;
            const controller = new AbortController();
            const id = setTimeout(() => controller.abort(), timeout);
            try {
                const response = await fetch(resource, { ...options, signal: controller.signal });
                clearTimeout(id);
                return response;
            } catch (err) {
                clearTimeout(id);
                throw err;
            }
        }

        async function onVerifyUser(e) {
            e.preventDefault();
            const mobile = document.getElementById('mobileInput').value.trim();
            const btn = document.getElementById('btnVerify');

            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-brand-cyan"></i> Querying Records...`;
            logTelemetry(`Querying Dreamstar database for mobile ${mobile}...`);

            try {
                const res = await fetchWithTimeout('/api/check-user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mobile }),
                    timeout: 20000
                });
                const data = await res.json();

                if (data.valid) {
                    verifiedMobile = data.mobile;
                    assignedEmail = data.assigned_email;

                    document.getElementById('profileCard').classList.remove('hidden');
                    document.getElementById('displayEmail').innerText = assignedEmail;
                    document.getElementById('displayExpiry').innerText = data.expiry_date || 'Active';

                    document.getElementById('badgeStep1').innerText = 'VERIFIED ✓';
                    document.getElementById('badgeStep1').className = 'text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800';

                    const actBox = document.getElementById('activationBox');
                    actBox.classList.remove('opacity-40', 'pointer-events-none');

                    showMessageStrip('success', `Mobile verified! Assigned Profile: ${assignedEmail}`);
                    logTelemetry(`Subscriber validated: ${assignedEmail} (Expiry: ${data.expiry_date})`, 'SUCCESS');
                } else {
                    showMessageStrip('error', data.message);
                    logTelemetry(`Validation failed: ${data.message}`, 'ERROR');
                }
            } catch (err) {
                const msg = err.name === 'AbortError' ? 'Verification request timed out.' : 'Server connection error.';
                showMessageStrip('error', msg);
                logTelemetry(`Server exception: ${msg}`, 'ERROR');
            } finally {
                btn.disabled = false;
                btn.innerHTML = `<i class="fa-solid fa-fingerprint text-brand-cyan"></i> <span>VERIFY SUBSCRIBER RECORD</span>`;
            }
        }

        async function onActivateTV(e) {
            e.preventDefault();
            const code = document.getElementById('tvCodeInput').value.trim();
            const btn = document.getElementById('btnActivate');

            if (!verifiedMobile || !assignedEmail) {
                showMessageStrip('error', 'Please verify your registered phone number first.');
                return;
            }

            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Initializing Headless Engine...`;
            logTelemetry(`Launching TV handshake for ${assignedEmail} with code ${code}...`);

            try {
                const res = await fetchWithTimeout('/api/activate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ mobile: verifiedMobile, code }),
                    timeout: 60000
                });
                const data = await res.json();

                if (data.formatted_output) {
                    document.getElementById('outputBox').classList.remove('hidden');
                    document.getElementById('outputText').value = data.formatted_output;
                }

                if (data.success) {
                    showMessageStrip('success', 'Television Connected Successfully! Enjoy streaming.');
                    logTelemetry(`TV code ${code} activated for ${assignedEmail}!`, 'SUCCESS');
                } else {
                    const errText = data.message || 'Activation failed.';
                    showMessageStrip('error', errText);
                    logTelemetry(`Activation failed: ${errText}`, 'ERROR');
                }
            } catch (err) {
                const msg = err.name === 'AbortError' ? 'Engine activation timed out. Please retry.' : 'Browser automation server error.';
                showMessageStrip('error', msg);
                logTelemetry(`Fatal exception: ${msg}`, 'ERROR');
            } finally {
                btn.disabled = false;
                btn.innerHTML = `<i class="fa-solid fa-tv"></i> <span>CONNECT TELEVISION NOW</span>`;
            }
        }

        function copyOutputText() {
            const txt = document.getElementById('outputText');
            txt.select();
            document.execCommand('copy');
            const btn = document.getElementById('btnCopy');
            btn.innerHTML = `<i class="fa-solid fa-check text-emerald-400"></i> <span>COPIED TO CLIPBOARD</span>`;
            setTimeout(() => {
                btn.innerHTML = `<i class="fa-solid fa-copy text-brand-cyan"></i> <span>Copy Summary To Clipboard</span>`;
            }, 2000);
        }
    </script>
</body>
</html>
"""

# Brand New Admin Panel UI
ADMIN_HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dreamstar Admin Control Room</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        brand: {
                            cyan: '#00f2fe',
                            blue: '#4facfe',
                            dark: '#070b12',
                            panel: '#0d1524',
                            border: '#1b2842'
                        }
                    },
                    fontFamily: {
                        cyber: ['"Chakra Petch"', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace']
                    }
                }
            }
        }
    </script>
    <style>
        body { background-color: #05080e; font-family: 'JetBrains Mono', monospace; }
        .cyber-card { background: rgba(13, 21, 36, 0.9); border: 1px solid #1b2842; }
    </style>
</head>
<body class="text-slate-300 min-h-screen p-4 md:p-8">

    <div class="max-w-6xl mx-auto space-y-6">

        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 cyber-card p-5 rounded-2xl">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-cyan to-brand-blue text-black font-black text-xl flex items-center justify-center font-cyber">
                    <i class="fa-solid fa-star"></i>
                </div>
                <div>
                    <h1 class="text-lg font-cyber font-bold text-white tracking-wide flex items-center gap-2">
                        DREAMSTAR <span class="text-brand-cyan">COMMAND CENTER</span>
                    </h1>
                    <p class="text-[11px] text-slate-400">Telemetry, Session Store & Step-by-Step Diagnostics</p>
                </div>
            </div>
            <a href="/" class="bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-brand-cyan px-4 py-2 rounded-xl text-xs font-bold transition border border-brand-border flex items-center gap-2">
                <i class="fa-solid fa-arrow-left"></i> Main Gateway
            </a>
        </div>

        <div id="loginBox" class="cyber-card max-w-md mx-auto p-6 rounded-2xl space-y-4 my-14">
            <div class="text-center font-cyber font-bold text-white text-base">
                <i class="fa-solid fa-lock text-brand-cyan mr-1"></i> Admin Authentication
            </div>
            <input type="password" id="adminKey" placeholder="Enter Admin Password"
                   class="w-full bg-slate-950 border border-brand-border rounded-xl p-3 text-white focus:outline-none focus:border-brand-cyan text-xs">
            <button onclick="onAdminLogin()" class="w-full bg-gradient-to-r from-brand-cyan to-brand-blue text-black font-cyber font-bold py-3 rounded-xl text-xs uppercase tracking-wider transition">
                Authenticate
            </button>
        </div>

        <div id="dashboardBox" class="hidden space-y-6">

            <!-- Metric Counters -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div class="cyber-card p-4 rounded-xl">
                    <div class="text-[10px] text-slate-500 uppercase">Pageviews</div>
                    <div id="metricViews" class="text-xl font-bold text-brand-cyan mt-1">0</div>
                </div>
                <div class="cyber-card p-4 rounded-xl">
                    <div class="text-[10px] text-slate-500 uppercase">Unique IPs</div>
                    <div id="metricVisitors" class="text-xl font-bold text-purple-400 mt-1">0</div>
                </div>
                <div class="cyber-card p-4 rounded-xl">
                    <div class="text-[10px] text-slate-500 uppercase">Success Hits</div>
                    <div id="metricSuccess" class="text-xl font-bold text-emerald-400 mt-1">0</div>
                </div>
                <div class="cyber-card p-4 rounded-xl">
                    <div class="text-[10px] text-slate-500 uppercase">Failed Hits</div>
                    <div id="metricFailed" class="text-xl font-bold text-rose-400 mt-1">0</div>
                </div>
            </div>

            <!-- In-Depth Diagnostic Logs -->
            <div class="cyber-card p-5 rounded-2xl space-y-4">
                <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 border-b border-brand-border/60 pb-3">
                    <div>
                        <h3 class="text-xs font-cyber font-bold text-brand-cyan uppercase tracking-wider">
                            <i class="fa-solid fa-microchip mr-1"></i> Real-time Execution Diagnostics
                        </h3>
                        <p class="text-[10px] text-slate-500">Inspect exact execution timestamps, URLs, and Netflix responses</p>
                    </div>
                    <div class="flex items-center gap-2">
                        <select id="filterLogSelect" onchange="renderDebugLogCards()" class="bg-slate-950 border border-brand-border rounded-lg px-2.5 py-1 text-[11px] text-slate-300 focus:outline-none">
                            <option value="ALL">All Traces</option>
                            <option value="FAILED">Failed Only</option>
                            <option value="SUCCESS">Success Only</option>
                        </select>
                        <button onclick="loadAdminStats()" class="bg-slate-900 text-[11px] px-3 py-1 rounded-lg text-slate-300 hover:text-white border border-brand-border">
                            <i class="fa-solid fa-rotate mr-1"></i> Refresh
                        </button>
                        <button onclick="clearDiagnosticLogs()" class="bg-rose-950/60 text-rose-300 text-[11px] px-3 py-1 rounded-lg border border-rose-900">
                            Clear
                        </button>
                    </div>
                </div>

                <div id="diagnosticFeed" class="space-y-3 max-h-96 overflow-y-auto pr-1"></div>
            </div>

            <!-- Cookie Profile Store -->
            <div class="cyber-card p-5 rounded-2xl space-y-4">
                <div class="flex justify-between items-center border-b border-brand-border/60 pb-3">
                    <h3 class="text-xs font-cyber font-bold text-white uppercase tracking-wider">Netflix Profiles & Cookie Store</h3>
                    <button onclick="fetchProfileList()" class="text-xs text-brand-cyan hover:underline">Refresh</button>
                </div>
                <div class="flex gap-2">
                    <input type="email" id="profileEmailInput" placeholder="profile@dreamstar.com"
                           class="flex-1 bg-slate-950 border border-brand-border rounded-xl px-3 py-2 text-xs text-white focus:outline-none font-mono">
                    <button onclick="createNewProfile()" class="bg-brand-cyan text-black font-cyber font-bold px-4 py-2 rounded-xl text-xs transition">
                        Add Profile
                    </button>
                </div>
                <div id="profilesBox" class="space-y-2 max-h-48 overflow-y-auto pr-1"></div>
            </div>

            <div id="cookieModal" class="hidden cyber-card p-5 rounded-2xl space-y-3 border-brand-cyan/40">
                <div class="flex justify-between items-center">
                    <h4 class="text-xs font-bold text-white uppercase">Cookies for: <span id="targetEmailLabel" class="text-brand-cyan font-mono"></span></h4>
                    <button onclick="closeCookieModal()" class="text-xs text-slate-500 hover:text-white">&times; Close</button>
                </div>
                <textarea id="cookieJsonTextarea" rows="6" placeholder="Paste JSON cookie array or raw string..."
                          class="w-full bg-slate-950 border border-brand-border rounded-xl p-3 text-xs font-mono text-slate-300 focus:outline-none"></textarea>
                <button onclick="saveCookiesToProfile()" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2.5 rounded-xl text-xs font-cyber uppercase transition">
                    Save Session Cookies
                </button>
            </div>

            <!-- Limits & Blacklist -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="cyber-card p-5 rounded-2xl space-y-3">
                    <h3 class="text-xs font-cyber font-bold text-white uppercase">Activation Limits</h3>
                    <div>
                        <label class="block text-[11px] text-slate-400 mb-1">Max Monthly (0 = Infinite)</label>
                        <input type="number" id="cfgMonthly" min="0" value="3" class="w-full bg-slate-950 border border-brand-border rounded-xl p-2.5 text-xs text-white">
                    </div>
                    <div>
                        <label class="block text-[11px] text-slate-400 mb-1">Max Lifetime (0 = Infinite)</label>
                        <input type="number" id="cfgLifetime" min="0" value="0" class="w-full bg-slate-950 border border-brand-border rounded-xl p-2.5 text-xs text-white">
                    </div>
                    <button onclick="saveLimitRules()" class="bg-slate-800 hover:bg-slate-700 text-brand-cyan border border-brand-border px-4 py-2 rounded-xl text-xs font-bold transition">
                        Update Limits
                    </button>
                </div>

                <div class="cyber-card p-5 rounded-2xl space-y-3">
                    <h3 class="text-xs font-cyber font-bold text-rose-400 uppercase">Blacklist Mobile</h3>
                    <div class="flex gap-2">
                        <input type="tel" id="blockNumberInput" placeholder="10-digit mobile" maxlength="10"
                               class="flex-1 bg-slate-950 border border-brand-border rounded-xl px-3 py-2 text-xs text-white font-mono">
                        <button onclick="blacklistNumber()" class="bg-rose-950 text-rose-300 border border-rose-900 px-4 py-2 rounded-xl text-xs font-bold transition">
                            Block
                        </button>
                    </div>
                    <p class="text-[10px] text-slate-500">Blocked numbers will receive an automated suspension prompt.</p>
                </div>
            </div>

            <!-- Server State Backup -->
            <div class="cyber-card p-5 rounded-2xl space-y-2">
                <h3 class="text-xs font-cyber font-bold text-white uppercase">Disaster Recovery (Persistent B64)</h3>
                <p class="text-[10px] text-slate-400">Copy this string and add it to Render's Environment Variables as <code class="text-brand-cyan">PROFILES_JSON_DATA</code> to ensure your profiles and logs survive free-tier redeploys.</p>
                <button onclick="copyB64Backup()" id="btnB64" class="w-full bg-slate-900 hover:bg-slate-800 text-brand-cyan border border-brand-border font-bold py-2.5 rounded-xl text-xs transition">
                    Export State Base64
                </button>
            </div>

        </div>

    </div>

    <script>
        let adminPass = "";
        let targetProfileEmail = "";
        let cachedDebugLogs = [];

        async function onAdminLogin() {
            const pwd = document.getElementById('adminKey').value;
            const res = await fetch('/api/admin/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: pwd })
            });
            const data = await res.json();
            if (data.success) {
                adminPass = pwd;
                document.getElementById('loginBox').classList.add('hidden');
                document.getElementById('dashboardBox').classList.remove('hidden');
                fetchProfileList();
                loadAdminStats();
            } else {
                alert('Invalid Admin Key');
            }
        }

        async function fetchProfileList() {
            const res = await fetch(`/api/admin/profiles?password=${encodeURIComponent(adminPass)}`);
            const data = await res.json();
            const box = document.getElementById('profilesBox');
            box.innerHTML = '';

            if (data.profiles && data.profiles.length > 0) {
                data.profiles.forEach(p => {
                    const row = document.createElement('div');
                    row.className = 'flex justify-between items-center bg-slate-950 p-3 rounded-xl border border-brand-border text-xs';
                    row.innerHTML = `
                        <div>
                            <span class="font-bold text-white font-mono">${p.email}</span>
                            <div class="text-[10px] ${p.has_cookies ? 'text-emerald-400' : 'text-rose-400'}">${p.has_cookies ? '✓ ' + p.cookie_count + ' cookies active' : '⚠ No cookies attached'}</div>
                        </div>
                        <div class="flex gap-2">
                            <button onclick="openCookieModal('${p.email}')" class="bg-slate-800 hover:bg-slate-700 text-brand-cyan border border-brand-border px-2.5 py-1 rounded-lg">Cookies</button>
                            <button onclick="removeProfile('${p.email}')" class="bg-rose-950/80 text-rose-300 px-2 py-1 rounded-lg">&times;</button>
                        </div>
                    `;
                    box.appendChild(row);
                });
            } else {
                box.innerHTML = `<div class="text-xs text-slate-500 italic p-2">No profiles registered yet.</div>`;
            }
        }

        async function loadAdminStats() {
            const res = await fetch(`/api/admin/stats?password=${encodeURIComponent(adminPass)}`);
            const data = await res.json();
            if (data) {
                document.getElementById('metricViews').innerText = data.pageviews || 0;
                document.getElementById('metricVisitors').innerText = data.unique_visitors || 0;
                document.getElementById('metricSuccess').innerText = data.successful_logs || 0;
                document.getElementById('metricFailed').innerText = data.failed_logs || 0;

                if (data.settings) {
                    document.getElementById('cfgMonthly').value = data.settings.max_monthly_activations ?? 3;
                    document.getElementById('cfgLifetime').value = data.settings.max_total_activations ?? 0;
                }

                cachedDebugLogs = data.debug_logs || [];
                renderDebugLogCards();
            }
        }

        function renderDebugLogCards() {
            const feed = document.getElementById('diagnosticFeed');
            feed.innerHTML = '';
            const filter = document.getElementById('filterLogSelect').value;

            let filtered = cachedDebugLogs;
            if (filter === 'FAILED') filtered = cachedDebugLogs.filter(l => !l.success);
            if (filter === 'SUCCESS') filtered = cachedDebugLogs.filter(l => l.success);

            if (!filtered || filtered.length === 0) {
                feed.innerHTML = `<div class="text-xs text-slate-500 italic p-4 text-center">No matching traces found.</div>`;
                return;
            }

            filtered.forEach(log => {
                const card = document.createElement('div');
                const isSuccess = log.success;
                card.className = `p-3 rounded-xl border ${isSuccess ? 'bg-slate-950/80 border-emerald-950' : 'bg-slate-950/80 border-rose-950'} text-xs space-y-2`;
                
                const stepsHtml = (log.steps && log.steps.length > 0)
                    ? log.steps.map(s => `<div class="text-[10px] font-mono ${s.includes('error') || s.includes('exception') || s.includes('rejected') ? 'text-rose-400' : 'text-slate-400'}">${s}</div>`).join('')
                    : '<div class="text-slate-500 text-[10px]">No step trace logged.</div>';

                card.innerHTML = `
                    <div class="flex justify-between items-start">
                        <div>
                            <span class="font-bold text-white font-mono">${log.mobile}</span>
                            <span class="text-slate-500 font-mono">(${log.email})</span>
                            <span class="text-brand-cyan font-mono ml-2">Code: ${log.code}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-slate-500 text-[10px]">${log.timestamp}</span>
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold ${isSuccess ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-rose-950 text-rose-400 border border-rose-800'}">
                                ${isSuccess ? 'SUCCESS' : 'FAILED'}
                            </span>
                        </div>
                    </div>
                    <div class="text-[11px] font-semibold ${isSuccess ? 'text-emerald-400' : 'text-rose-400'}">
                        ${log.message}
                    </div>
                    <details class="bg-black/60 p-2 rounded-lg border border-slate-900">
                        <summary class="text-slate-500 text-[10px] cursor-pointer hover:text-white uppercase font-bold">
                            View Execution Trace (${log.steps ? log.steps.length : 0} steps)
                        </summary>
                        <div class="mt-2 space-y-1 pl-1 border-l border-slate-800">
                            ${stepsHtml}
                        </div>
                    </details>
                `;
                feed.appendChild(card);
            });
        }

        async function clearDiagnosticLogs() {
            if (!confirm("Clear execution diagnostics?")) return;
            await fetch('/api/admin/debug-logs/clear', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: adminPass })
            });
            loadAdminStats();
        }

        function openCookieModal(email) {
            targetProfileEmail = email;
            document.getElementById('targetEmailLabel').innerText = email;
            document.getElementById('cookieModal').classList.remove('hidden');
        }

        function closeCookieModal() {
            document.getElementById('cookieModal').classList.add('hidden');
        }

        async function saveCookiesToProfile() {
            const cookiesRaw = document.getElementById('cookieJsonTextarea').value;
            const res = await fetch('/api/admin/profiles/cookies', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    password: adminPass,
                    email: targetProfileEmail,
                    cookies: cookiesRaw
                })
            });
            const data = await res.json();
            if (data.success) {
                alert(`Cookies saved for ${targetProfileEmail}!`);
                closeCookieModal();
                document.getElementById('cookieJsonTextarea').value = '';
                fetchProfileList();
            } else {
                alert(`Error: ${data.message}`);
            }
        }

        async function createNewProfile() {
            const email = document.getElementById('profileEmailInput').value.trim();
            if (!email) return;
            await fetch('/api/admin/profiles/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: adminPass, email })
            });
            document.getElementById('profileEmailInput').value = '';
            fetchProfileList();
        }

        async function removeProfile(email) {
            if (!confirm(`Delete profile ${email}?`)) return;
            await fetch('/api/admin/profiles/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: adminPass, email })
            });
            fetchProfileList();
        }

        async function saveLimitRules() {
            const monthly = parseInt(document.getElementById('cfgMonthly').value) || 0;
            const total = parseInt(document.getElementById('cfgLifetime').value) || 0;
            await fetch('/api/admin/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    password: adminPass,
                    settings: { max_monthly_activations: monthly, max_total_activations: total }
                })
            });
            alert('Limit rules saved.');
        }

        async function blacklistNumber() {
            const mob = document.getElementById('blockNumberInput').value.trim();
            if (!mob) return;
            await fetch('/api/admin/block-number', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: adminPass, mobile: mob, block: true })
            });
            document.getElementById('blockNumberInput').value = '';
            alert(`Mobile ${mob} blacklisted.`);
        }

        async function copyB64Backup() {
            const res = await fetch('/api/admin/export-env', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: adminPass })
            });
            const data = await res.json();
            if (data.b64_str) {
                navigator.clipboard.writeText(data.b64_str);
                const btn = document.getElementById('btnB64');
                btn.innerText = "✓ Copied to Clipboard!";
                setTimeout(() => { btn.innerText = "Export State Base64"; }, 2500);
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    record_pageview(client_ip)
    return HTML_CONTENT

@app.get("/admin", response_class=HTMLResponse)
async def serve_admin_page(request: Request):
    return ADMIN_HTML_CONTENT

@app.post("/api/check-user")
async def api_check_user(data: dict = Body(...)):
    mobile = data.get("mobile", "")
    sheet_url = data.get("sheet_url", DEFAULT_SHEET_URL)
    
    allowed, limit_msg = check_activation_limit(mobile)
    if not allowed:
        return {"valid": False, "error_code": "LIMIT_OR_BLOCKED", "message": limit_msg}

    res = fetch_and_validate_user(mobile_number=mobile, custom_sheet_url=sheet_url)
    return res

@app.post("/api/activate")
async def api_activate(data: dict = Body(...)):
    mobile = data.get("mobile", "")
    code = data.get("code", "")
    sheet_url = data.get("sheet_url", DEFAULT_SHEET_URL)

    allowed, limit_msg = check_activation_limit(mobile)
    if not allowed:
        log_activation(mobile=mobile, email="Unknown", code=code, success=False, message=limit_msg)
        return {"success": False, "error_code": "LIMIT_OR_BLOCKED", "message": limit_msg}

    validation = fetch_and_validate_user(mobile_number=mobile, custom_sheet_url=sheet_url)
    if not validation.get("valid"):
        log_activation(mobile=mobile, email="Unknown", code=code, success=False, message=validation.get("message"))
        return validation

    assigned_email = validation.get("assigned_email")
    expiry_date = validation.get("expiry_date", "")

    res = await activate_tv(email=assigned_email, raw_code=code, mobile=mobile, expiry_date=expiry_date)
    
    log_activation(
        mobile=mobile,
        email=assigned_email,
        code=code,
        success=res.get("success", False),
        message=res.get("message", "")
    )
    
    return res

@app.post("/api/admin/login")
async def admin_login(data: dict = Body(...)):
    pwd = data.get("password", "")
    if pwd == ADMIN_PASSWORD:
        return {"success": True}
    return JSONResponse({"success": False, "message": "Invalid Password"}, status_code=401)

@app.get("/api/admin/profiles")
async def admin_list_profiles(password: str):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"profiles": get_all_profiles()}

@app.get("/api/admin/stats")
async def admin_get_stats(password: str):
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return get_activation_stats()

@app.post("/api/admin/debug-logs/clear")
async def admin_clear_debug(data: dict = Body(...)):
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    clear_debug_logs()
    return {"success": True}

@app.post("/api/admin/block-number")
async def admin_block_number(data: dict = Body(...)):
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    mobile = data.get("mobile", "")
    block = data.get("block", True)
    blocked_list = toggle_block_number(mobile, block)
    return {"success": True, "blocked_numbers": blocked_list}

@app.post("/api/admin/settings")
async def admin_update_settings(data: dict = Body(...)):
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    new_s = update_settings(data.get("settings", {}))
    return {"success": True, "settings": new_s}

@app.post("/api/admin/profiles/add")
async def admin_add_profile(data: dict = Body(...)):
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    add_or_update_profile(email=data.get("email", ""))
    return {"success": True}

@app.post("/api/admin/profiles/delete")
async def admin_delete_profile(data: dict = Body(...)):
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    delete_profile(email=data.get("email", ""))
    return {"success": True}

@app.post("/api/admin/profiles/cookies")
async def admin_update_cookies(data: dict = Body(...)):
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    email = data.get("email", "")
    cookies_raw = data.get("cookies")
    add_or_update_profile(email=email, cookies_raw=cookies_raw)
    return {"success": True}

@app.post("/api/admin/export-env")
async def admin_export_env(data: dict = Body(...)):
    if data.get("password") != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"b64_str": export_full_state_b64()}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
