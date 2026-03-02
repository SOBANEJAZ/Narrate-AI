"""Streamlit Web UI for Narrate-AI - Cinematic Documentary Studio

This module provides a cinematic web interface for generating documentaries.
Features a film-archive aesthetic with 3D particle timeline visualization.

"""

import os
import shlex
import subprocess
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()


APP_ROOT = Path(__file__).resolve().parent
MAIN_SCRIPT = APP_ROOT / "main.py"

DEFAULT_MAX_WEBSITES = 4
DEFAULT_TTS_PROVIDER = "elevenlabs"


THREE_JS_CANVAS = """
<div id="cinematic-canvas-container">
    <canvas id="cinematic-canvas"></canvas>
    <div class="film-grain-overlay"></div>
    <div class="vignette-overlay"></div>
    <div class="light-streaks" id="light-streaks"></div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
(function() {
    const container = document.getElementById('cinematic-canvas-container');
    const canvas = document.getElementById('cinematic-canvas');
    
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    
    const particleCount = 2000;
    const particles = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const sizes = new Float32Array(particleCount);
    
    const colorPalette = [
        new THREE.Color(0xe11d48),
        new THREE.Color(0xd4a853),
        new THREE.Color(0xfef3c7),
        new THREE.Color(0x78716c),
        new THREE.Color(0xf5f5f4)
    ];
    
    for (let i = 0; i < particleCount; i++) {
        const i3 = i * 3;
        const angle = (i / particleCount) * Math.PI * 4;
        const radius = 3 + Math.random() * 2;
        const y = (Math.random() - 0.5) * 8;
        
        positions[i3] = Math.cos(angle) * radius + (Math.random() - 0.5) * 0.5;
        positions[i3 + 1] = y;
        positions[i3 + 2] = Math.sin(angle) * radius + (Math.random() - 0.5) * 0.5;
        
        const color = colorPalette[Math.floor(Math.random() * colorPalette.length)];
        colors[i3] = color.r;
        colors[i3 + 1] = color.g;
        colors[i3 + 2] = color.b;
        
        sizes[i] = Math.random() * 3 + 1;
    }
    
    particles.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particles.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    particles.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
    
    const particleMaterial = new THREE.PointsMaterial({
        size: 0.05,
        vertexColors: true,
        transparent: true,
        opacity: 0.8,
        blending: THREE.AdditiveBlending,
        sizeAttenuation: true
    });
    
    const particleSystem = new THREE.Points(particles, particleMaterial);
    scene.add(particleSystem);
    
    const timelineCurve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(-8, 0, 0),
        new THREE.Vector3(-4, 2, 0),
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(4, -2, 0),
        new THREE.Vector3(8, 0, 0)
    ]);
    
    const tubeGeometry = new THREE.TubeGeometry(timelineCurve, 100, 0.02, 8, false);
    const tubeMaterial = new THREE.MeshBasicMaterial({ 
        color: 0xe11d48, 
        transparent: true, 
        opacity: 0.3 
    });
    const timeline = new THREE.Mesh(tubeGeometry, tubeMaterial);
    scene.add(timeline);
    
    const filmReelGeometry = new THREE.TorusGeometry(0.8, 0.15, 8, 32);
    const filmReelMaterial = new THREE.MeshBasicMaterial({ color: 0xd4a853, wireframe: true });
    
    const reels = [];
    const reelPositions = [-6, -3, 0, 3, 6];
    reelPositions.forEach((x, i) => {
        const reel = new THREE.Mesh(filmReelGeometry, filmReelMaterial.clone());
        reel.position.set(x, 0, 0);
        reel.rotation.y = Math.random() * Math.PI;
        reels.push(reel);
        scene.add(reel);
    });
    
    camera.position.z = 8;
    camera.position.y = 1;
    
    let mouseX = 0;
    let mouseY = 0;
    let targetX = 0;
    let targetY = 0;
    
    document.addEventListener('mousemove', (event) => {
        mouseX = (event.clientX / window.innerWidth) * 2 - 1;
        mouseY = -(event.clientY / window.innerHeight) * 2 + 1;
    });
    
    const clock = new THREE.Clock();
    
    function animate() {
        requestAnimationFrame(animate);
        
        const elapsed = clock.getElapsedTime();
        
        targetX += (mouseX * 0.5 - targetX) * 0.02;
        targetY += (mouseY * 0.3 - targetY) * 0.02;
        
        particleSystem.rotation.y = elapsed * 0.05;
        particleSystem.rotation.x = Math.sin(elapsed * 0.2) * 0.1;
        
        const positions = particleSystem.geometry.attributes.position.array;
        for (let i = 0; i < particleCount; i++) {
            const i3 = i * 3;
            positions[i3 + 1] += Math.sin(elapsed + i * 0.01) * 0.001;
        }
        particleSystem.geometry.attributes.position.needsUpdate = true;
        
        reels.forEach((reel, i) => {
            reel.rotation.z = elapsed * 0.5 * (i % 2 === 0 ? 1 : -1);
            reel.position.y = Math.sin(elapsed + i) * 0.3;
        });
        
        camera.position.x += (targetX - camera.position.x) * 0.02;
        camera.position.y += (targetY + 1 - camera.position.y) * 0.02;
        camera.lookAt(0, 0, 0);
        
        renderer.render(scene, camera);
    }
    
    animate();
    
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
    
    window.triggerFilmGlow = function() {
        const lightStreaks = document.getElementById('light-streaks');
        lightStreaks.classList.add('active');
        setTimeout(() => lightStreaks.classList.remove('active'), 2000);
    };
})();
</script>
"""


CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Oswald:wght@300;400;500;600&family=Source+Sans+3:wght@300;400;500;600&display=swap');

:root {
    --bg-deep: #0a0a0c;
    --bg-surface: #141418;
    --bg-elevated: #1c1c21;
    --primary: #e11d48;
    --primary-glow: #e11d4880;
    --secondary: #d4a853;
    --secondary-dim: #d4a85340;
    --text-primary: #f5f5f4;
    --text-muted: #78716c;
    --text-dim: #44403c;
    --accent-light: #fef3c7;
    --border: #27272a;
    --film-grain-opacity: 0.04;
}

* {
    font-family: 'Source Sans 3', sans-serif !important;
}

#cinematic-canvas-container {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    height: 100vh !important;
    z-index: -1 !important;
    pointer-events: none !important;
}

#cinematic-canvas {
    width: 100% !important;
    height: 100% !important;
}

.film-grain-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    opacity: var(--film-grain-opacity);
    pointer-events: none;
    mix-blend-mode: overlay;
}

.vignette-overlay {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: radial-gradient(ellipse at center, transparent 40%, rgba(0,0,0,0.7) 100%);
    pointer-events: none;
}

.light-streaks {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(120deg, transparent 30%, rgba(254,243,199,0.03) 50%, transparent 70%);
    opacity: 0;
    transition: opacity 0.5s ease;
}

.light-streaks.active {
    opacity: 1;
    animation: lightSweep 2s ease-in-out;
}

@keyframes lightSweep {
    0% { transform: translateX(-100%) skewX(-20deg); }
    50% { transform: translateX(100%) skewX(-20deg); }
    100% { transform: translateX(100%) skewX(-20deg); }
}

section[data-testid="stApp"] {
    background: transparent !important;
}

.main-content {
    position: relative;
    z-index: 1;
    padding: 2rem;
    max-width: 1200px;
    margin: 0 auto;
}

/* Logo & Header */
.logo-container {
    text-align: center;
    padding: 3rem 0 2rem;
    animation: fadeInDown 0.8s ease-out;
}

@keyframes fadeInDown {
    from {
        opacity: 0;
        transform: translateY(-30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.logo-text {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 4rem !important;
    letter-spacing: 0.15em !important;
    background: linear-gradient(135deg, var(--text-primary) 0%, var(--secondary) 50%, var(--primary) 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    text-shadow: none !important;
    margin-bottom: 0.5rem !important;
}

.logo-tagline {
    font-family: 'Oswald', sans-serif !important;
    font-weight: 300 !important;
    font-size: 1.1rem !important;
    color: var(--text-muted) !important;
    letter-spacing: 0.3em !important;
    text-transform: uppercase !important;
}

.logo-icon {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}

.logo-icon svg {
    width: 48px;
    height: 48px;
    color: var(--secondary);
    animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 0.8; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.05); }
}

/* Pipeline Stages */
.pipeline-container {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin: 2rem 0;
    animation: fadeIn 1s ease-out 0.3s both;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.pipeline-stage {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.25rem;
    background: linear-gradient(135deg, var(--bg-elevated) 0%, var(--bg-surface) 100%);
    border: 1px solid var(--border);
    border-radius: 4px;
    transition: all 0.3s ease;
    cursor: default;
}

.pipeline-stage:hover {
    border-color: var(--secondary);
    box-shadow: 0 0 20px var(--secondary-dim);
    transform: translateY(-2px);
}

.pipeline-stage.active {
    border-color: var(--primary);
    box-shadow: 0 0 25px var(--primary-glow);
}

.pipeline-stage.completed {
    border-color: #22c55e;
}

.pipeline-icon {
    width: 20px;
    height: 20px;
    color: var(--text-muted);
}

.pipeline-stage.active .pipeline-icon {
    color: var(--primary);
    animation: iconPulse 1s ease-in-out infinite;
}

@keyframes iconPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.pipeline-label {
    font-family: 'Oswald', sans-serif !important;
    font-weight: 400 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
}

.pipeline-arrow {
    color: var(--text-dim) !important;
    font-size: 1.2rem !important;
}

/* Input Section */
.input-section {
    background: linear-gradient(180deg, var(--bg-surface) 0%, rgba(20,20,24,0.8) 100%);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 2rem;
    margin: 2rem 0;
    backdrop-filter: blur(10px);
    animation: slideUp 0.6s ease-out 0.5s both;
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.input-label {
    font-family: 'Oswald', sans-serif !important;
    font-weight: 400 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.2em !important;
    text-transform: uppercase !important;
    color: var(--secondary) !important;
    margin-bottom: 0.75rem !important;
    display: block;
}

.topic-input-wrapper {
    position: relative;
    margin-bottom: 1.5rem;
}

.topic-input-wrapper::before {
    content: '';
    position: absolute;
    left: -20px;
    top: 50%;
    transform: translateY(-50%);
    width: 16px;
    height: 16px;
    background: var(--secondary);
    clip-path: polygon(0 0, 100% 0, 100% 30%, 60% 30%, 60% 100%, 0 100%);
}

.topic-input-wrapper input {
    background: var(--bg-deep) !important;
    border: 2px solid var(--border) !important;
    border-radius: 4px !important;
    padding: 1rem 1.5rem !important;
    font-size: 1.25rem !important;
    color: var(--text-primary) !important;
    font-family: 'Oswald', sans-serif !important;
    font-weight: 300 !important;
    letter-spacing: 0.05em !important;
    transition: all 0.3s ease !important;
}

.topic-input-wrapper input:focus {
    border-color: var(--secondary) !important;
    box-shadow: 0 0 20px var(--secondary-dim) !important;
    outline: none !important;
}

.topic-input-wrapper input::placeholder {
    color: var(--text-dim) !important;
}

/* Config Columns */
.config-columns {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.5rem;
    margin-bottom: 1.5rem;
}

.config-item label {
    font-family: 'Oswald', sans-serif !important;
    font-weight: 400 !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
}

/* TTS Section */
.tts-section {
    padding: 1rem;
    background: var(--bg-deep);
    border: 1px solid var(--border);
    border-radius: 4px;
    margin-bottom: 1.5rem;
}

.tts-header {
    font-family: 'Oswald', sans-serif !important;
    font-weight: 400 !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
    margin-bottom: 0.75rem !important;
}

/* Radio buttons */
.tts-section div[data-baseweb="radio-group"] {
    gap: 1rem !important;
}

.tts-section div[data-baseweb="radio-group"] label {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    padding: 0.75rem 1.25rem !important;
    border-radius: 4px !important;
    transition: all 0.3s ease !important;
}

.tts-section div[data-baseweb="radio-group"] label:hover {
    border-color: var(--secondary) !important;
}

.tts-section div[data-baseweb="radio-group"] label[aria-checked="true"] {
    border-color: var(--primary) !important;
    background: var(--bg-elevated) !important;
    box-shadow: 0 0 15px var(--primary-glow) !important;
}

/* Generate Button */
.generate-btn button {
    background: linear-gradient(135deg, var(--primary) 0%, #be123c 100%) !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 1rem 3rem !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1.5rem !important;
    letter-spacing: 0.2em !important;
    color: var(--text-primary) !important;
    transition: all 0.3s ease !important;
    position: relative;
    overflow: hidden;
}

.generate-btn button::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    transition: left 0.5s ease;
}

.generate-btn button:hover::before {
    left: 100%;
}

.generate-btn button:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 40px var(--primary-glow) !important;
}

/* Warning/Info Messages */
.stAlert {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    padding: 1rem !important;
}

.stAlert[data-testid="stMarkdownContainer"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}

/* Terminal/Logs */
.terminal-container {
    background: #0a0a0a !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
    overflow: hidden;
    margin: 2rem 0;
}

.terminal-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border);
}

.terminal-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
}

.terminal-dot.red { background: #ef4444; }
.terminal-dot.yellow { background: #eab308; }
.terminal-dot.green { background: #22c55e; }

.terminal-title {
    font-family: 'Oswald', sans-serif !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.1em !important;
    color: var(--text-muted) !important;
    margin-left: auto;
}

.terminal-content {
    padding: 1rem;
    font-family: 'JetBrains Mono', 'Fira Code', monospace !important;
    font-size: 0.85rem !important;
    line-height: 1.6 !important;
    max-height: 400px;
    overflow-y: auto;
}

.terminal-content code {
    color: var(--accent-light) !important;
    background: transparent !important;
}

/* Film Leader Decorations */
.terminal-content::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 20px;
    background: repeating-linear-gradient(
        90deg,
        transparent,
        transparent 9px,
        var(--text-dim) 9px,
        var(--text-dim) 10px
    );
    opacity: 0.3;
}

/* Video Player */
.video-container {
    position: relative;
    background: var(--bg-deep);
    border: 3px solid var(--secondary);
    border-radius: 8px;
    overflow: hidden;
    margin: 2rem 0;
    box-shadow: 0 0 60px rgba(212, 168, 83, 0.2);
}

.video-frame {
    position: relative;
    padding: 20px;
    background: linear-gradient(180deg, var(--bg-surface) 0%, var(--bg-deep) 100%);
}

.video-frame::before,
.video-frame::after {
    content: '★';
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    font-size: 2rem;
    color: var(--secondary);
    opacity: 0.5;
}

.video-frame::before { left: 10px; }
.video-frame::after { right: 10px; }

.video-title {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1rem !important;
    letter-spacing: 0.2em !important;
    color: var(--secondary) !important;
    text-align: center;
    margin-bottom: 0.5rem !important;
}

/* Output Paths */
.output-paths {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1rem;
    margin: 1rem 0;
}

.output-path {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 4px;
}

.output-path-icon {
    width: 20px;
    height: 20px;
    color: var(--secondary);
}

.output-path-text {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.8rem !important;
    color: var(--text-muted) !important;
    word-break: break-all;
}

/* Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-deep);
}

::-webkit-scrollbar-thumb {
    background: var(--border);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--text-dim);
}

/* Expander */
.streamlit-expander {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 4px !important;
}

.streamlit-expander header {
    font-family: 'Oswald', sans-serif !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.1em !important;
    color: var(--text-muted) !important;
}

/* Success Message */
.stSuccess {
    background: linear-gradient(135deg, rgba(34,197,94,0.1) 0%, rgba(34,197,94,0.05) 100%) !important;
    border: 1px solid #22c55e !important;
    color: #22c55e !important;
}

/* Error Message */
.stError {
    background: linear-gradient(135deg, rgba(239,68,68,0.1) 0%, rgba(239,68,68,0.05) 100%) !important;
    border: 1px solid #ef4444 !important;
    color: #ef4444 !important;
}

/* Hide default streamlit elements */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }

/* Responsive */
@media (max-width: 768px) {
    .logo-text {
        font-size: 2.5rem !important;
    }
    
    .pipeline-container {
        flex-direction: column;
    }
    
    .pipeline-arrow {
        transform: rotate(90deg);
    }
    
    .config-columns {
        grid-template-columns: 1fr;
    }
}
</style>
"""


def _build_command(topic, max_websites, tts_provider):
    return [
        sys.executable,
        str(MAIN_SCRIPT),
        topic,
        "--max-websites",
        str(max_websites),
        "--tts-provider",
        tts_provider,
    ]


def _extract_value(logs, prefix):
    for line in reversed(logs):
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return None


def render_3d_canvas():
    st.markdown(THREE_JS_CANVAS, unsafe_allow_html=True)


def render_custom_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header():
    st.markdown(
        f"""
    <div class="logo-container">
        <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"/>
                <polygon points="10,8 16,12 10,16" fill="currentColor" stroke="none"/>
            </svg>
            <span class="logo-text">NARRATE-AI</span>
        </div>
        <p class="logo-tagline">Transform any topic into cinematic documentary</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_pipeline():
    stages = [
        ("search", "Research", True),
        ("file-text", "Script", False),
        ("image", "Images", False),
        ("volume-2", "Narration", False),
        ("film", "Export", False),
    ]

    stage_html = '<div class="pipeline-container">'
    for i, (icon, label, active) in enumerate(stages):
        active_class = "active" if active else ""
        icon_svg = get_icon(icon)
        stage_html += f"""
        <div class="pipeline-stage {active_class}">
            <svg class="pipeline-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                {icon_svg}
            </svg>
            <span class="pipeline-label">{label}</span>
        </div>
        """
        if i < len(stages) - 1:
            stage_html += '<span class="pipeline-arrow">→</span>'

    stage_html += "</div>"
    st.markdown(stage_html, unsafe_allow_html=True)


def get_icon(name):
    icons = {
        "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>',
        "file-text": '<path d="M14 2H2 0 6a2 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
        "image": '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
        "volume-2": '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>',
        "film": '<rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="2" y1="7" x2="7" y2="7"/><line x1="2" y1="17" x2="7" y2="17"/><line x1="17" y1="17" x2="22" y2="17"/><line x1="17" y1="7" x2="22" y2="7"/>',
    }
    return icons.get(name, "")


def render_terminal(logs):
    if not logs:
        return

    st.markdown(
        f"""
    <div class="terminal-container">
        <div class="terminal-header">
            <span class="terminal-dot red"></span>
            <span class="terminal-dot yellow"></span>
            <span class="terminal-dot green"></span>
            <span class="terminal-title">PRODUCTION LOG</span>
        </div>
        <div class="terminal-content">
            <code>{chr(10).join(logs)}</code>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_video_player(video_path):
    if not video_path or not Path(video_path).exists():
        return

    st.markdown(
        f"""
    <div class="video-container">
        <div class="video-frame">
            <p class="video-title">FINAL OUTPUT</p>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.video(str(video_path))


def render_output_paths(logs):
    run_dir = _extract_value(logs, "Run directory:")
    script_path = _extract_value(logs, "Script:")
    timeline_path = _extract_value(logs, "Timeline:")
    manifest_path = _extract_value(logs, "Manifest:")
    final_video = _extract_value(logs, "Final video:")

    paths = [
        ("folder", "Run Directory", run_dir),
        ("file-text", "Script", script_path),
        ("calendar", "Timeline", timeline_path),
        ("database", "Manifest", manifest_path),
        ("film", "Final Video", final_video),
    ]

    path_html = '<div class="output-paths">'
    for icon, label, value in paths:
        if value:
            icon_svg = get_icon(icon)
            path_html += f"""
            <div class="output-path">
                <svg class="output-path-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    {icon_svg}
                </svg>
                <span class="output-path-text">{label}: {value}</span>
            </div>
            """
    path_html += "</div>"

    if any(p[2] for p in paths):
        st.markdown(path_html, unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="Narrate-AI | Documentary Generator",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    render_custom_css()
    render_3d_canvas()

    st.markdown('<div class="main-content">', unsafe_allow_html=True)

    render_header()
    render_pipeline()

    with st.container():
        st.markdown('<div class="input-section">', unsafe_allow_html=True)

        topic = st.text_input(
            "Topic",
            value="Apollo Program",
            help="Enter any historical topic, event, person, or concept",
            key="topic_input",
        )

        col1, col2 = st.columns(2)
        with col1:
            max_websites = st.number_input(
                "Max Websites",
                min_value=1,
                step=1,
                value=DEFAULT_MAX_WEBSITES,
                help="Number of websites to research, the model also will use its own knowledge base to generate the script, so you can keep it low.",
            )

        has_elevenlabs_key = bool(os.getenv("ELEVENLABS_API_KEY"))

        tts_provider = st.radio(
            "TTS Provider",
            options=["elevenlabs", "edge_tts"],
            index=0 if DEFAULT_TTS_PROVIDER == "elevenlabs" else 1,
            horizontal=True,
        )

        if tts_provider == "elevenlabs" and not has_elevenlabs_key:
            st.warning(
                "⚠️ ElevenLabs API key not found. Set ELEVENLABS_API_KEY or use Edge TTS."
            )

        if tts_provider == "edge_tts":
            st.info("ℹ️ Edge TTS: Free Microsoft voices, no API key required.")

        st.markdown("</div>", unsafe_allow_html=True)

    run_clicked = st.button(
        "▶ GENERATE DOCUMENTARY", type="primary", use_container_width=True
    )

    if not run_clicked:
        st.markdown("</div>", unsafe_allow_html=True)
        return

    topic = topic.strip()
    if not topic:
        st.error("Topic is required.")
        return

    command = _build_command(
        topic=topic,
        max_websites=int(max_websites),
        tts_provider=tts_provider,
    )

    log_box = st.empty()
    logs = []
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    process = subprocess.Popen(
        command,
        cwd=str(APP_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None
    for line in process.stdout:
        logs.append(line.rstrip("\n"))
        with log_box.container():
            render_terminal(logs)

    return_code = process.wait()

    if return_code != 0:
        st.error(f"Pipeline failed with exit code {return_code}.")
        return

    st.success("✓ Documentary generated successfully!")

    render_output_paths(logs)

    final_video = _extract_value(logs, "Final video:")
    if final_video and Path(final_video).exists():
        render_video_player(final_video)

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
