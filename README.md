# COSwatch
a cosmic watcher
🌌 C-0-MOS: Kinetic Defense & NEO Surveillance System"Vigilance is our only defense."A real-time, 3D visualization platform for tracking Near-Earth Objects (NEOs), analyzing kinetic impact risks, and simulating orbital defense scenarios.🚀 Mission OverviewC-0-MOS (Computation-0-Module for Orbital Surveillance) is a web-based tactical interface that visualizes data from NASA's Center for Near-Earth Object Studies (CNEOS). 

Unlike standard 2D lists, this system renders asteroids in a physically accurate 3D solar system, allowing users to understand the scale, velocity, and trajectory of potentially hazardous objects relative to Earth.

🌟 Key FeaturesReal-Time 3D Surveillance: View the Solar System, Earth, and live asteroids in a fully interactive WebGL environment.Kinetic Impact Analysis: "Ultra Research Mode" calculates impact energy (Megatons), blast radius, and spectral composition using real physics.Third-Person "Ride" Mechanic: Click any asteroid to lock the camera and "ride" it through space in a PUBG-style 3rd person view.

Defense Alert System: Automated browser notifications and tactical HUD counters when hazardous objects ($R_{score} > 80\%$) are detected.Community Uplink: A simulated encrypted network for researchers to upload and share thesis data (mock functionality).

🛠️ Tech Stack & ArchitectureThis project is built with vanilla web technologies to ensure maximum performance and compatibility, leveraging powerful libraries for 3D rendering and animation.

ComponentTechnologyDescriptionFrontend CoreHTML5, JavaScript (ES6+)No framework overhead; raw performance.

3D EngineThree.jsHandles WebGL rendering, shaders, and scene management.StylingTailwind CSSUtility-first CSS for the "Sci-Fi / Cyberpunk" HUD aesthetic.AnimationGSAP (GreenSock)Smooth camera transitions and UI micro-interactions.


Data SourceNASA NeoWs APIFetches live asteroid telemetry (Velocity, Diameter, Miss Distance).MathBox3 / RaycastingUsed for precise 3D object selection and camera collision handling.📸 Interface Modules1. Tactical Command (Main View)The central hub. Users can toggle between Solar System View (macro scale) and Earth View (micro scale). 


The HUD displays live velocity vectors and distance units in Lunar Distances (LD).2. "Ultra Research" TerminalA dedicated modal for deep analysis.Input: Object Diameter ($D$) and Relative Velocity ($V_{rel}$).


Output: Kinetic Energy in Megatons ($E_k = \frac{1}{2}mv^2$), estimated thermal blast radius, and physical composition (Albedo/Spectral Type).3. Community UplinkA simulated peer-review feed where users can "upload" observations. This module demonstrates frontend state management and mock API interaction (simulating network latency and success states).⚡ Installation & SetupSince C-0-MOS is built with vanilla JS, it requires no complex build steps (like Webpack or Vite) to run locally.PrerequisitesA modern web browser (Chrome/Firefox/Edge) with WebGL support.


VS Code (recommended) or any code editor.Live Server extension (recommended for local CORS handling).Quick StartClone the RepositoryBashgit clone https://github.com/perlin-cyber-god/COSwatch.git


cd c0mos-defense-system


Add AssetsEnsure you have an assets folder or backend folder containing your research graphs:velocity_dist_graph.

pngorbit_inclination_graph.pngRun LocallyOpen index.html with Live Server (Right-click -> "Open with Live Server").

Note: Just double-clicking the file might block texture loading due to browser security policies (CORS).🧠 Scientific Context (The "Why")This project references the NEO Surveyor mission profile.Grav, T., Mainzer, A. K., et al. (2023). The NEO Surveyor Near-Earth Asteroid Known Object Model. The Planetary Science Journal, 4:228.The application implements the C-0-MOS Risk Algorithm, a normalized threat index derived from the paper's findings on the completion rate of Near-Earth Objects >140m. We specifically highlight the "City Killer" class (50m - 140m) which often escapes detection until close approach.


🔮 Future Roadmap[ ] VR Module: WebXR integration for "standing" on asteroids in Virtual Reality.[ ] Real Backend: Connect to a Node.js/Express server for persistent user accounts and real community uploads.[ ] Deflection Sim: A mini-game module to test Kinetic Impactor deflection strategies (DART Mission style).