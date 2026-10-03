import { useEffect, useRef } from "react";
import * as THREE from "three";
export function ControlScene({ value }: { value: number }) {
  const mount = useRef<HTMLDivElement>(null),
    target = useRef(value);
  useEffect(() => {
    target.current = value;
  }, [value]);
  useEffect(() => {
    const el = mount.current;
    if (!el) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      el.textContent = "3D unavailable. Decoder output remains visible above.";
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.set(0, 2.5, 8);
    camera.lookAt(0, 0, 0);
    const grid = new THREE.GridHelper(14, 28, 0x29443c, 0x182a2c);
    grid.position.y = -0.9;
    scene.add(grid);
    const geometry = new THREE.IcosahedronGeometry(0.58, 2);
    const material = new THREE.MeshStandardMaterial({
      color: 0x76e7c2,
      metalness: 0.45,
      roughness: 0.25,
      wireframe: false,
    });
    const orb = new THREE.Mesh(geometry, material);
    scene.add(orb);
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(geometry),
      new THREE.LineBasicMaterial({
        color: 0xb1ffe4,
        transparent: true,
        opacity: 0.3,
      }),
    );
    orb.add(edges);
    const light = new THREE.PointLight(0x8affd4, 40);
    light.position.set(2, 3, 3);
    scene.add(light, new THREE.AmbientLight(0x95b5d0, 1.4));
    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(0.85, 0.01, 8, 64),
      new THREE.MeshBasicMaterial({ color: 0x5fcfae }),
    );
    ring.rotation.x = Math.PI / 2;
    ring.position.y = -0.8;
    scene.add(ring);
    const trailGeo = new THREE.BufferGeometry();
    const trailMat = new THREE.LineBasicMaterial({
      color: 0x5bbba6,
      transparent: true,
      opacity: 0.45,
    });
    const trail = new THREE.Line(trailGeo, trailMat);
    scene.add(trail);
    const points: THREE.Vector3[] = [];
    const resize = () => {
      renderer.setSize(el.clientWidth, el.clientHeight);
      camera.aspect = el.clientWidth / el.clientHeight;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(el);
    resize();
    let handle = 0;
    const animate = (t: number) => {
      handle = requestAnimationFrame(animate);
      orb.position.x += (target.current * 2.7 - orb.position.x) * 0.035;
      orb.position.y = Math.sin(t * 0.0012) * 0.08;
      orb.rotation.y += 0.003;
      ring.position.x = orb.position.x;
      points.push(orb.position.clone());
      if (points.length > 100) points.shift();
      trailGeo.setFromPoints(points);
      renderer.render(scene, camera);
    };
    handle = requestAnimationFrame(animate);
    return () => {
      cancelAnimationFrame(handle);
      observer.disconnect();
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      trailGeo.dispose();
      trailMat.dispose();
      scene.traverse((o) => {
        if (o instanceof THREE.Mesh || o instanceof THREE.LineSegments) {
          o.geometry.dispose();
          if (!Array.isArray(o.material)) o.material.dispose();
        }
      });
      el.removeChild(renderer.domElement);
    };
  }, []);
  return (
    <div
      className="scene"
      ref={mount}
      aria-label="3D control object. Left and right position follows the displayed decision."
    />
  );
}
