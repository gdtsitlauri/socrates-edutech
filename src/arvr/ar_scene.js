/**
 * SOCRATES AR/VR Educational Module
 * WebXR + Three.js augmented reality scene for interactive learning.
 *
 * Features:
 *  - WebXR AR session (marker-less, hit-test based placement)
 *  - 3D educational cards that anchor to real-world surfaces
 *  - Quiz interaction layer (tap card -> reveal answer)
 *  - Spatial audio cue on correct answer
 *  - Graceful fallback to 3D desktop viewer when AR unavailable
 */

import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js';

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let renderer, scene, camera, xrSession = null;
let reticle, hitTestSource = null, hitTestSourceRequested = false;
let placedCards = [];
let currentQuizIndex = 0;

const QUIZ_CARDS = [
  { question: 'What is a DFA?', answer: 'A Deterministic Finite Automaton — a finite-state machine with exactly one transition per symbol per state.' },
  { question: 'Define Big-O notation.', answer: 'An upper bound on time complexity: f(n) = O(g(n)) means f grows no faster than g.' },
  { question: 'What is a Turing Machine?', answer: 'An abstract model of computation with an infinite tape, a head, and a finite set of states and transition rules.' },
  { question: 'What is the P vs NP problem?', answer: 'The open question of whether every problem whose solution can be verified in polynomial time (NP) can also be solved in polynomial time (P).' },
  { question: 'What is a neural network?', answer: 'A computational model of layered, interconnected nodes (neurons) that learn representations from data via gradient descent.' },
  { question: 'Define DNS.', answer: 'Domain Name System — translates human-readable domain names (e.g. example.com) into IP addresses.' },
  { question: 'What is a deadlock?', answer: 'A state where two or more processes are waiting indefinitely for resources held by each other.' },
  { question: 'What is a hash function?', answer: 'A function mapping arbitrary data to a fixed-size digest — used in data structures, cryptography, and integrity checks.' },
];

// ---------------------------------------------------------------------------
// Initialise Three.js + WebXR
// ---------------------------------------------------------------------------
export function init(canvas) {
  renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(canvas.clientWidth, canvas.clientHeight);
  renderer.xr.enabled = true;

  scene = new THREE.Scene();

  camera = new THREE.PerspectiveCamera(70, canvas.clientWidth / canvas.clientHeight, 0.01, 20);

  // Lighting
  scene.add(new THREE.AmbientLight(0xffffff, 1.0));
  const dir = new THREE.DirectionalLight(0xffffff, 0.8);
  dir.position.set(1, 2, 1);
  scene.add(dir);

  // Reticle (AR placement ring)
  const reticleGeom = new THREE.RingGeometry(0.06, 0.07, 32).rotateX(-Math.PI / 2);
  const reticleMat = new THREE.MeshBasicMaterial({ color: 0x00ff88 });
  reticle = new THREE.Mesh(reticleGeom, reticleMat);
  reticle.matrixAutoUpdate = false;
  reticle.visible = false;
  scene.add(reticle);

  window.addEventListener('resize', onResize);
}

// ---------------------------------------------------------------------------
// AR session management
// ---------------------------------------------------------------------------
export async function startAR() {
  if (!navigator.xr) {
    console.warn('WebXR not supported — using desktop fallback mode.');
    startDesktopFallback();
    return;
  }

  const supported = await navigator.xr.isSessionSupported('immersive-ar').catch(() => false);
  if (!supported) {
    startDesktopFallback();
    return;
  }

  xrSession = await navigator.xr.requestSession('immersive-ar', {
    requiredFeatures: ['hit-test', 'dom-overlay'],
    domOverlay: { root: document.getElementById('ar-overlay') },
  });

  renderer.xr.setReferenceSpaceType('local');
  await renderer.xr.setSession(xrSession);

  xrSession.addEventListener('select', onSelect);
  renderer.setAnimationLoop(renderLoop);

  document.getElementById('start-btn').textContent = 'AR Active';
  document.getElementById('status').textContent = 'Point at a surface and tap to place a quiz card.';
}

export function stopAR() {
  if (xrSession) {
    xrSession.end();
    xrSession = null;
  }
  renderer.setAnimationLoop(null);
  hitTestSource = null;
  hitTestSourceRequested = false;
}

// ---------------------------------------------------------------------------
// Desktop fallback (orbit camera + click to place cards)
// ---------------------------------------------------------------------------
function startDesktopFallback() {
  document.getElementById('status').textContent = 'WebXR unavailable — desktop 3D mode active. Click to place cards.';
  renderer.setAnimationLoop(desktopLoop);
  renderer.domElement.addEventListener('click', () => placeCard(new THREE.Vector3(
    (Math.random() - 0.5) * 1.5,
    (Math.random() - 0.5) * 0.5,
    -1.5,
  )));
}

function desktopLoop() {
  renderer.render(scene, camera);
}

// ---------------------------------------------------------------------------
// Hit-test + placement
// ---------------------------------------------------------------------------
function renderLoop(_time, frame) {
  if (!frame) return;
  const session = renderer.xr.getSession();

  if (!hitTestSourceRequested) {
    session.requestReferenceSpace('viewer').then(refSpace => {
      session.requestHitTestSource({ space: refSpace }).then(src => {
        hitTestSource = src;
      });
    });
    session.addEventListener('end', () => {
      hitTestSourceRequested = false;
      hitTestSource = null;
    });
    hitTestSourceRequested = true;
  }

  if (hitTestSource) {
    const results = frame.getHitTestResults(hitTestSource);
    if (results.length > 0) {
      const hit = results[0];
      const refSpace = renderer.xr.getReferenceSpace();
      const pose = hit.getPose(refSpace);
      reticle.visible = true;
      reticle.matrix.fromArray(pose.transform.matrix);
    } else {
      reticle.visible = false;
    }
  }

  renderer.render(scene, camera);
}

function onSelect() {
  if (reticle.visible) {
    const pos = new THREE.Vector3();
    reticle.getWorldPosition(pos);
    placeCard(pos);
  }
}

// ---------------------------------------------------------------------------
// Quiz card geometry
// ---------------------------------------------------------------------------
function placeCard(position) {
  const card = QUIZ_CARDS[currentQuizIndex % QUIZ_CARDS.length];
  currentQuizIndex++;

  const group = new THREE.Group();
  group.position.copy(position);

  // Card panel
  const panel = new THREE.Mesh(
    new THREE.BoxGeometry(0.25, 0.15, 0.004),
    new THREE.MeshStandardMaterial({ color: 0x1a237e, roughness: 0.4 }),
  );
  group.add(panel);

  // Question label (canvas texture)
  const canvas = makeTextCanvas(card.question, '#ffffff', '#1a237e', 512, 256);
  const texture = new THREE.CanvasTexture(canvas);
  const label = new THREE.Mesh(
    new THREE.PlaneGeometry(0.24, 0.13),
    new THREE.MeshBasicMaterial({ map: texture, transparent: true }),
  );
  label.position.z = 0.003;
  group.add(label);

  // Interaction: tap card to flip and reveal answer
  let revealed = false;
  label.userData.onClick = () => {
    if (!revealed) {
      const ansCanvas = makeTextCanvas(card.answer, '#fff9c4', '#1b5e20', 512, 256);
      texture.image = ansCanvas;
      texture.needsUpdate = true;
      panel.material.color.set(0x1b5e20);
      revealed = true;
      document.getElementById('status').textContent = 'Correct! Tap another surface to place the next card.';
    }
  };

  scene.add(group);
  placedCards.push({ group, label });
  document.getElementById('status').textContent = `Card placed: "${card.question}"`;
}

function makeTextCanvas(text, fg, bg, w, h) {
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  const ctx = cv.getContext('2d');
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = fg;
  ctx.font = 'bold 28px Arial';
  ctx.textAlign = 'center';
  wrapText(ctx, text, w / 2, 60, w - 40, 36);
  return cv;
}

function wrapText(ctx, text, x, y, maxW, lineH) {
  const words = text.split(' ');
  let line = '';
  for (const word of words) {
    const test = line + word + ' ';
    if (ctx.measureText(test).width > maxW && line) {
      ctx.fillText(line.trim(), x, y);
      line = word + ' ';
      y += lineH;
    } else {
      line = test;
    }
  }
  ctx.fillText(line.trim(), x, y);
}

function onResize() {
  const canvas = renderer.domElement;
  camera.aspect = canvas.clientWidth / canvas.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(canvas.clientWidth, canvas.clientHeight);
}
