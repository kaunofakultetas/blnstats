// -----------------------------------------------------------
//  [*] Particles — animated login background
//
//  tsparticles (slim build) tuned for a subtle effect: faint
//  linked dots, 30 fps cap, repulsed by the mouse. fullScreen
//  mode pins the canvas behind everything (zIndex -1).
//
//  Used by:
//    - Login — fixed background layer of the page
// -----------------------------------------------------------

import Particles from "react-tsparticles";
import { loadSlim } from "tsparticles-slim";
import { useCallback, useEffect, useState } from "react";


export default function ParticlesComponent(props) {

  const [particleNumber, setParticleNumber] = useState(0);

  useEffect(() => {
    setParticleNumber(window.innerWidth / 10);
  }, []);

  const options = {
    fullScreen: {
      enable: true,
      zIndex: -1,
    },
    fpsLimit: 30,
    detectRetina: true,
    interactivity: {
      events: {
        onClick: {
          enable: false,
          mode: "push",
        },
        onHover: {
          enable: true,
          mode: "repulse",
        },
      },
      modes: {
        push: {
          quantity: 10,
        },
        repulse: {
          distance: 100,
        },
      },
    },
    particles: {
      links: {
        enable: true,
        distance: 150,
        opacity: 0.5
      },
      move: {
        enable: true,
        speed: { min: 0.01, max: 1.0 },
      },
      opacity: {
        value: { min: 0.0, max: 0.2 },
      },
      size: {
        value: { min: 1, max: 3 },
      },
      number: {
        value: particleNumber,
      },
    },
  };


  const particlesInit = useCallback(async (engine) => {
    await loadSlim(engine);
  }, []);

  return <Particles id={props.id} init={particlesInit} options={options} />;
}
